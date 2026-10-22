const $ = (id) => document.getElementById(id);
let offset = 0,
  limit = 0,
  busy = false;
const pageSize = 20;
function show(text, kind = "") {
  const el = $("message");
  el.textContent = text;
  el.className = "message " + kind;
  el.hidden = false;
}
function headers() {
  return $("apiKey").value ? { "X-API-Key": $("apiKey").value } : {};
}
async function api(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    headers: { ...headers(), ...(options.headers || {}) },
  });
  if (!r.ok) {
    let detail = "HTTP " + r.status;
    try {
      const b = await r.json();
      detail =
        typeof b.detail === "string" ? b.detail : JSON.stringify(b.detail);
    } catch {}
    throw new Error(detail);
  }
  return r;
}
function bytes(n) {
  return n < 1024
    ? n + " B"
    : n < 1048576
      ? (n / 1024).toFixed(1) + " KB"
      : (n / 1048576).toFixed(2) + " MB";
}
async function health() {
  try {
    const r = await fetch("/health/ready");
    if (!r.ok) throw new Error();
    const data = await r.json();
    limit = data.max_file_bytes;
    $("status").textContent = "Sẵn sàng · " + data.storage;
    $("status").className = "status ok";
    $("limit").textContent = "Tối đa " + bytes(limit) + " mỗi tệp.";
  } catch {
    $("status").textContent = "Dịch vụ chưa sẵn sàng";
    $("status").className = "status";
  }
}
function cell(row, text, cls) {
  const td = document.createElement("td");
  td.textContent = text;
  if (cls) td.className = cls;
  row.append(td);
  return td;
}
async function refresh() {
  try {
    const data = await (
      await api("/api/files?offset=" + offset + "&limit=" + pageSize)
    ).json();
    $("files").replaceChildren();
    for (const item of data) {
      const tr = document.createElement("tr");
      const td = cell(tr, "");
      const name = document.createElement("span");
      name.className = "filename";
      name.textContent = item.filename;
      const hash = document.createElement("span");
      hash.className = "hash";
      hash.textContent = item.sha256;
      td.append(name, hash);
      cell(tr, bytes(item.size));
      cell(tr, new Date(item.created_at).toLocaleString("vi-VN"));
      const actions = cell(tr, "");
      const wrap = document.createElement("div");
      wrap.className = "actions";
      for (const [label, fn] of [
        ["Tải xuống", () => download(item)],
        ["Verify", () => verify(item)],
      ]) {
        const b = document.createElement("button");
        b.textContent = label;
        b.className = "secondary";
        b.onclick = async () => {
          b.disabled = true;
          try {
            await fn();
          } catch (e) {
            show(e.message, "error");
          } finally {
            b.disabled = false;
          }
        };
        wrap.append(b);
      }
      actions.append(wrap);
      $("files").append(tr);
    }
    if (!data.length) {
      const tr = document.createElement("tr");
      const td = cell(tr, "Chưa có tệp ở trang này.", "empty");
      td.colSpan = 4;
      $("files").append(tr);
    }
    $("prev").disabled = offset === 0;
    $("next").disabled = data.length < pageSize;
    $("page").textContent = "Trang " + (offset / pageSize + 1);
  } catch (e) {
    show("Không đọc được danh sách: " + e.message, "error");
  }
}
async function download(item) {
  const r = await api("/api/files/" + item.id + "/download");
  const url = URL.createObjectURL(await r.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = item.filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function verify(item) {
  const r = await (
    await api("/api/files/" + item.id + "/verify", { method: "POST" })
  ).json();
  show(
    (r.intact ? "TOÀN VẸN" : "PHÁT HIỆN THAY ĐỔI") +
      " · " +
      item.filename +
      "\nSHA-256 gốc: " +
      r.expected_sha256 +
      "\nSHA-256 hiện tại: " +
      r.actual_sha256 +
      "\nDung lượng: " +
      r.actual_size +
      " / " +
      r.expected_size +
      " byte",
    r.intact ? "success" : "error",
  );
}
$("uploadForm").onsubmit = async (e) => {
  e.preventDefault();
  if (busy) return;
  const file = $("file").files[0];
  if (!file) return;
  if (limit && file.size > limit) {
    show("Tệp vượt giới hạn " + bytes(limit), "error");
    return;
  }
  busy = true;
  $("upload").disabled = true;
  show("Đang tải lên " + file.name + "…");
  try {
    await api("/api/files?filename=" + encodeURIComponent(file.name), {
      method: "POST",
      headers: { "Content-Type": "application/octet-stream" },
      body: file,
    });
    show("Đã lưu tệp và SHA-256: " + file.name, "success");
    $("file").value = "";
    offset = 0;
    await refresh();
  } catch (e) {
    show("Tải lên thất bại: " + e.message, "error");
  } finally {
    busy = false;
    $("upload").disabled = false;
  }
};
$("refresh").onclick = () => {
  health();
  refresh();
};
$("apiKey").onchange = () => {
  offset = 0;
  refresh();
};
$("prev").onclick = () => {
  offset = Math.max(0, offset - pageSize);
  refresh();
};
$("next").onclick = () => {
  offset += pageSize;
  refresh();
};
for (const event of ["dragenter", "dragover"])
  $("drop").addEventListener(event, (e) => {
    e.preventDefault();
    $("drop").classList.add("drag");
  });
$("drop").addEventListener("dragleave", () =>
  $("drop").classList.remove("drag"),
);
$("drop").addEventListener("drop", (e) => {
  e.preventDefault();
  $("drop").classList.remove("drag");
  if (e.dataTransfer.files.length) $("file").files = e.dataTransfer.files;
});
health();
refresh();
