// Tempel di script.google.com (akun Drive yang sama), ganti SECRET, lalu Deploy > Web app
// Execute as: Me | Who has access: Anyone
const SECRET = "GANTI_DENGAN_TOKEN_RAHASIA";
const FOLDERS = {
  "Still Prabowo": "14-mA7dM7xEYjF43EERs8Be_n6BgozWNv",
  "Political Party": "1DSapFdEOeFUGX6Q7hkd32ZdwAWaBGQue",
  "Info Nahdliyyin": "1Vx1bIpMvSH9mflr37Uox0QGg_NPHUzh3",
  "Spek Dulu": "1PiWoXUk6nyy58WB0Guxjnv0UhdzM9QSo",
  "Blitar Nyaman": "1piMtKOR9TU1fv9y5j3vtFexsPLe4XlYB",
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
