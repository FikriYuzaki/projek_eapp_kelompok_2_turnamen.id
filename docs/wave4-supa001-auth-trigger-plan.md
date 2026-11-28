# Rencana Migrasi Wave 4 — SUPA-001: Hardening Auth User Signup Trigger

Dokumen ini merupakan hasil investigasi dan rancangan migrasi Wave 4 untuk menutup temuan **SUPA-001** tanpa memodifikasi `supabase/migrations/0001_initial_schema.sql` maupun `supabase/migrations/0002_security_hardening.sql`, dan **belum diterapkan ke Supabase Cloud**.

---

## 1. Akar Masalah pada `0002_security_hardening.sql`

Pada `supabase/migrations/0002_security_hardening.sql` baris 169–214 (`public.handle_new_auth_user()`):

```sql
    UPDATE public.profiles
    SET auth_user_id = NEW.id,
        phone = COALESCE(public.profiles.phone, v_phone),
        updated_at = NOW()
    WHERE LOWER(email) = LOWER(NEW.email)
      AND auth_user_id IS NULL;

    IF NOT FOUND THEN
        INSERT INTO public.profiles (id, auth_user_id, email, username, full_name, role, phone, is_active)
        VALUES (NEW.id, NEW.id, LOWER(NEW.email), v_username, v_full_name, v_safe_role, v_phone, TRUE)
        ON CONFLICT (auth_user_id) DO NOTHING;
    END IF;
```

### Celah Keamanan yang Ditemukan

1. **Auto-Link Berdasarkan `LOWER(email)` Memungkinkan Account Takeover Profil Privileged (`auth_user_id IS NULL`):**
   - Jika terdapat baris `public.profiles` yang belum terhubung ke `auth.users` (`auth_user_id IS NULL`)—misalnya profil seed awal atau akun pra-buat untuk `super_admin`, `organizer`, atau `committee`—siapa pun yang mendaftar melalui Supabase Auth public signup dengan email tersebut akan otomatis diikat (`auth_user_id = NEW.id`) ke profil tersebut oleh trigger.
   - Meskipun trigger membatasi `v_safe_role` ke `('player', 'team_captain')` pada cabang `INSERT`, cabang `UPDATE ... WHERE LOWER(email) = LOWER(NEW.email) AND auth_user_id IS NULL` **tetap mempertahankan role asli** dari baris `public.profiles` yang ditargetkan (`super_admin` / `organizer` / `committee`).
2. **Eksekusi Terjadi pada `AFTER INSERT ON auth.users` Sebelum Verifikasi Email:**
   - Pada alur signup standar, `NEW.email_confirmed_at` dapat bernilai `NULL` saat row `auth.users` pertama kali dibuat, sehingga auto-link berbasis email terjadi bahkan sebelum kepemilikan email tervalidasi.
3. **Mutasi Kolom `phone` dari `raw_user_meta_data` saat Auto-Link:**
   - Trigger juga mengisi `phone` profil target dari `NEW.raw_user_meta_data->>'phone'` milik pendaftar baru.

---

## 2. Tujuan Desain Migrasi Wave 4 (`0004_supa001_auth_trigger_hardening.sql`)

1. **Menghapus total mekanisme auto-link `LOWER(email)`** dari `public.handle_new_auth_user()`.
2. **Memastikan signup publik hanya membuat profil baru dengan role `player` atau `team_captain`**, dan **gagal secara aman / ditolak** jika email sudah terdaftar di `public.profiles` (tidak pernah menempel ke baris `public.profiles` yang sudah ada, khususnya profil privileged dengan `auth_user_id IS NULL`).
3. **Memindahkan provisioning akun privileged (`super_admin`, `organizer`, `committee`)** ke jalur eksplisit terotorisasi yang tidak mengandalkan `raw_user_meta_data` sebagai sumber keputusan otorisasi.
4. **Menjaga signup normal (`player`, `team_captain`) tetap berjalan** tanpa gangguan.

---

## 3. Rancangan SQL Migrasi Wave 4 (Belum Diterapkan ke Cloud)

```sql
-- Turnamen.in: Wave 4 SUPA-001 Auth Trigger Hardening (DRAFT PLAN — DO NOT APPLY YET)
-- Target file nantinya: supabase/migrations/0005_supa001_auth_trigger_hardening.sql

-- 1. Pastikan schema private tersedia untuk RPC provisioning privileged
CREATE SCHEMA IF NOT EXISTS private;
REVOKE ALL ON SCHEMA private FROM PUBLIC, anon;

-- 2. Ganti trigger function handle_new_auth_user() agar TIDAK pernah melakukan auto-link LOWER(email)
CREATE OR REPLACE FUNCTION public.handle_new_auth_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
    v_requested_role VARCHAR(32);
    v_safe_role VARCHAR(32);
    v_username VARCHAR(60);
    v_full_name VARCHAR(120);
    v_phone VARCHAR(40);
    v_clean_email TEXT;
    v_existing_profile RECORD;
BEGIN
    v_clean_email := LOWER(TRIM(COALESCE(NEW.email, '')));
    IF v_clean_email = '' THEN
        RAISE EXCEPTION 'Email akun Auth tidak boleh kosong.' USING ERRCODE = '22023';
    END IF;

    -- Pastikan signup tidak menempel atau membajak profile yang sudah ada (termasuk unlinked privileged row)
    SELECT id, role, auth_user_id
    INTO v_existing_profile
    FROM public.profiles
    WHERE LOWER(email) = v_clean_email
    LIMIT 1;

    IF FOUND THEN
        RAISE EXCEPTION 'Email sudah terdaftar pada profil lain dan tidak dapat ditautkan otomatis.'
            USING ERRCODE = '23505';
    END IF;

    -- Role publik pada self-signup tetap dibatasi ke player / team_captain
    v_requested_role := COALESCE(LOWER(TRIM(NEW.raw_user_meta_data->>'role')), 'player');
    IF v_requested_role IN ('player', 'team_captain') THEN
        v_safe_role := v_requested_role;
    ELSE
        v_safe_role := 'player';
    END IF;

    v_username := COALESCE(
        NULLIF(TRIM(NEW.raw_user_meta_data->>'username'), ''),
        SPLIT_PART(v_clean_email, '@', 1) || '_' || SUBSTR(REPLACE(NEW.id::text, '-', ''), 1, 6)
    );
    v_full_name := COALESCE(
        NULLIF(TRIM(NEW.raw_user_meta_data->>'full_name'), ''),
        v_username
    );
    v_phone := NULLIF(TRIM(NEW.raw_user_meta_data->>'phone'), '');

    INSERT INTO public.profiles (
        id, auth_user_id, email, username, full_name, role, phone, is_active
    )
    VALUES (
        NEW.id, NEW.id, v_clean_email, v_username, v_full_name, v_safe_role, v_phone, TRUE
    )
    ON CONFLICT (auth_user_id) DO NOTHING;

    RETURN NEW;
END;
$$;

REVOKE ALL ON FUNCTION public.handle_new_auth_user() FROM PUBLIC, anon, authenticated;
```

### Catatan Keamanan Penting pada `auth.users` & `INSERT` Race

- Karena `profiles.email` sudah memiliki constraint `UNIQUE`, pemeriksaan `SELECT ... WHERE LOWER(email) = v_clean_email` ditambah `UNIQUE INDEX` case-insensitive (`CREATE UNIQUE INDEX IF NOT EXISTS uq_profiles_lower_email ON public.profiles (LOWER(email));`) memastikan dua signup bersamaan dengan huruf besar/kecil berbeda tetap tertahan oleh constraint `23505` tanpa auto-link.
- Pada Supabase Auth, jika trigger mengangkat exception (`23505`), transaksi pembuatan `auth.users` ikut di-rollback sehingga tidak tercipta akun auth yatim yang bisa mengakses API.

---

## 4. Mekanisme Aman Provisioning Akun Privileged (`super_admin`, `organizer`, `committee`)

Prinsip utama: **Otoritas role TIDAK PERNAH dibaca dari `raw_user_meta_data`** yang bisa disisipkan saat public signup.

### Alur yang Direkomendasikan

1. **Jalankan Invite / Admin Auth Creation Terlebih Dahulu:**
   - Administrator (`super_admin`) atau skrip provisioning server menggunakan Supabase Admin API (`auth.admin.inviteUserByEmail` atau `auth.admin.createUser` dengan `email_confirm: true`) **tanpa** menyisipkan `role` privileged di `user_metadata`.
   - Trigger `handle_new_auth_user()` hanya akan membuat profil awal dengan role default `'player'` yang sudah terikat langsung ke `auth_user_id = NEW.id`.
2. **Promosi / Penetapan Role Eksplisit oleh `super_admin` via RPC Terotorisasi:**
   - Buat RPC `private.assign_user_role(p_target_profile_id UUID, p_new_role VARCHAR)` (dipanggil melalui wrapper `public.assign_user_role` ber-atribut `SECURITY INVOKER` dan `REVOKE ALL FROM PUBLIC, anon`):
     - Memvalidasi `auth.uid()` milik pemanggil aktif di `public.profiles` dengan `role = 'super_admin'` (dan `is_active = TRUE`).
     - Memvalidasi `p_new_role IN ('player', 'team_captain', 'committee', 'organizer', 'super_admin')`.
     - Memastikan profil target sudah memiliki `auth_user_id IS NOT NULL` (akun Auth valid yang tidak mengandalkan `auth_user_id IS NULL`).
     - Mencatat perubahan ke `public.activity_logs` (`action = 'USER_ROLE_UPDATED'`) untuk jejak audit.
3. **Untuk Seed / Akun Awal Lingkungan Dev/Prod:**
   - Semua akun seed (`admin@turnamen.in`, `organizer@turnamen.in`, `committee@turnamen.in`) **wajib** diprovisioning ke `auth.users` terlebih dahulu lalu `auth_user_id` di-bind secara eksplisit lewat ID `auth.users.id` dalam proses bootstrap terkendali—**tidak pernah** menyisakan baris privileged di `public.profiles` dengan `auth_user_id IS NULL`.

---

## 5. Daftar Verifikasi Sebelum & Sesudah Penerapan Wave 4

1. Signup user baru melalui `auth.sign_up` dengan `user_metadata = {"role": "super_admin"}` -> profil baru tetap mendapat `role = 'player'`, bukan `super_admin`.
2. Jika ada baris `public.profiles` bersisa dengan `auth_user_id IS NULL` (baik `super_admin`, `organizer`, maupun `committee`), `auth.sign_up` dengan email yang sama **wajib ditolak** dan `auth_user_id` target tetap `NULL` (tidak tertaut).
3. Signup normal untuk `player` dan `team_captain` (dengan email belum terdaftar) tetap membuat baris `public.profiles` berstatus `is_active = TRUE` secara otomatis.
4. Promosi role menjadi `committee` / `organizer` oleh non-`super_admin` ditolak (`42501`), sedangkan oleh `super_admin` terautentikasi berhasil dan tercatat pada `activity_logs`.
