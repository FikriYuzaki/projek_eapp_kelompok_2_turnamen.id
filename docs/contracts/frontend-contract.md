# Kontrak Frontend & Desktop Bridge — Turnamen.in

Dokumen ini menetapkan kesepakatan antarmuka antara **Ferlita** (UI/UX & Halaman Frontend) dan **Fikri** (Python Eel Bridge & Core JavaScript Client).

---

## 1. Arsitektur Komunikasi Frontend

Di dalam jendela desktop Turnamen.in (`desktop/web/`), halaman dan komponen UI **tidak boleh** memanggil `fetch()` mentah secara tersebar. Seluruh komunikasi wajib melewati modul inti di `desktop/web/assets/js/core/`:

1. `window.TurnamenConfig` (`config.js`): Menyimpan konfigurasi runtime frontend, status mode (`mock` atau `supabase`), dan sesi pengguna aktif di memori/localStorage.
2. `window.TurnamenAPI` (`api-client.js`): Klien terpusat yang memanggil Flask REST API (`/api/v1/*`) atau meneruskan permintaan melalui Python Eel Bridge bila tersedia.
3. `window.TurnamenBridge` (`eel-bridge.js`): Wrapper aman di sekitar `window.eel` agar halaman tetap dapat dibuka dan diuji baik melalui jendela Python Eel maupun browser lokal saat pengembangan UI.

---

## 2. Kontrak Method `window.TurnamenAPI`

Seluruh method di bawah ini bersifat `async` dan mengembalikan Promise dengan struktur `{ success, message, data, error }`:

```javascript
// Health & Runtime Info
await TurnamenAPI.getHealth();

// Authentication & Role Simulation (Mock Mode)
await TurnamenAPI.login(email, password);
await TurnamenAPI.register(payload);
await TurnamenAPI.logout();
await TurnamenAPI.getCurrentUser();
TurnamenAPI.setSimulatedRole(roleName); // Khusus pengujian UI pada APP_MODE=mock

// Games
await TurnamenAPI.getGames();
await TurnamenAPI.getGameById(gameId);

// Tournaments
await TurnamenAPI.getTournaments(filters);
await TurnamenAPI.getTournamentById(tournamentId);
await TurnamenAPI.createTournament(payload);
await TurnamenAPI.updateTournament(tournamentId, payload);
await TurnamenAPI.deleteTournament(tournamentId);

// Teams & Members
await TurnamenAPI.getTeams();
await TurnamenAPI.getTeamById(teamId);
await TurnamenAPI.createTeam(payload);
await TurnamenAPI.updateTeam(teamId, payload);
await TurnamenAPI.addTeamMember(teamId, payload);

// Registrations
await TurnamenAPI.getTournamentRegistrations(tournamentId);
await TurnamenAPI.registerTeamToTournament(tournamentId, payload);
await TurnamenAPI.updateRegistrationStatus(registrationId, status, notes);

// Matches & Bracket
await TurnamenAPI.getTournamentMatches(tournamentId);
await TurnamenAPI.generateBracket(tournamentId);
await TurnamenAPI.submitMatchResult(matchId, { score_a, score_b, notes });

// Announcements & Reports
await TurnamenAPI.getAnnouncements(tournamentId);
await TurnamenAPI.createAnnouncement(tournamentId, payload);
await TurnamenAPI.getTournamentReport(tournamentId);
await TurnamenAPI.getTournamentStandings(tournamentId);
```

---

## 3. Kontrak Komponen UI (`window.TurnamenUI`)

File `desktop/web/assets/js/components/ui-components.js` menyediakan helper standar untuk digunakan di seluruh halaman:
- `TurnamenUI.renderStatusBadge(status)`: Merender `<span class="badge badge-...">` dengan warna dan teks Bahasa Indonesia yang konsisten.
- `TurnamenUI.renderLoadingState(message)`: Merender tampilan pemuatan data.
- `TurnamenUI.renderEmptyState(title, subtitle, actionHtml)`: Merender state kosong ketika belum ada data.
- `TurnamenUI.renderErrorState(message, retryCallbackName)`: Merender pesan gagal muat beserta tombol coba lagi.
- `TurnamenUI.showToast(message, type)`: Menampilkan notifikasi toast (`info`, `success`, `warning`, `danger`).
- `TurnamenUI.openModal({ title, bodyHtml, footerHtml })` & `TurnamenUI.closeModal()`: Mengelola dialog modal aplikasi.

---

## 4. Daftar 10 Halaman Wajib (`data-page`)

Navigasi aplikasi mendukung 10 view utama yang templatenya terdokumentasi di `desktop/web/pages/` dan dirender secara responsif di shell utama:
1. `login` — Halaman masuk & simulasi pemilihan akun 5 role (dalam mode mock).
2. `dashboard` — Ringkasan metrik, turnamen aktif, jadwal terdekat, dan pengumuman terbaru.
3. `tournament-list` — Katalog turnamen dengan pencarian, filter status/game, dan tombol buat turnamen.
4. `tournament-detail` — Informasi lengkap turnamen, aturan, kuota, daftar peserta, dan status verifikasi.
5. `team-management` — Daftar tim e-sport, detail kapten, dan pengelolaan roster pemain (`ingame_id`).
6. `match-management` — Daftar jadwal pertandingan per babak dan form pengesahan skor oleh panitia/organizer.
7. `bracket` — Visualisasi bagan Single Elimination (Quarter Final → Semi Final → Grand Final).
8. `announcements` — Papan pengumuman resmi turnamen dengan penanda prioritas (`urgent`, `important`, `normal`).
9. `reports` — Laporan statistik turnamen, persentase penyelesaian pertandingan, dan tabel klasemen akhir (*standings*).
10. `profile` — Informasi akun aktif, role, hak akses, dan status lingkungan aplikasi.
