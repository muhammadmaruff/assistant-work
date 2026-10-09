// Tempel di script.google.com (akun Drive yang sama), ganti SECRET, lalu Deploy > Web app
// Execute as: Me | Who has access: Anyone
const SECRET = "GANTI_DENGAN_TOKEN_RAHASIA";
const FOLDERS = {
  "bicarablitar.com": "1akHh_fWNgwoFKtFfYnTGcj2K5UFVk2Wv",
  "impas.id": "1_LOTiJlqfvaWin9CrwWWHDyhGYSB1oMd",
  "jatimverse.id": "1jS-tWjpi148bamjqwJGOz0-h2FlrSMq3",
  "pecelblitar.com": "1oTwVZs25M4jmEFJViPQfjqv16KMK8Fa7",
  "serayunusantara.com": "1xWS1LaccU60AwE8QV83JkcInHGkRTHGp",
};

function doPost(e) {
  const d = JSON.parse(e.postData.contents);
  if (d.token !== SECRET || !FOLDERS[d.media]) return out({ ok: false, error: "ditolak" });
  const folder = DriveApp.getFolderById(FOLDERS[d.media]);
  d.files.forEach((f) => folder.createFile(f.name, f.content, MimeType.PLAIN_TEXT));
  return out({ ok: true, saved: d.files.length });
}

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
