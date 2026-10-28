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
function api(url, options = {}, config = {}) {
  return IntegrityClient.request(
    url,
    {
      ...options,
      headers: { ...headers(), ...(options.headers || {}) },
    },
    config,
  );
}
async function copy(hash) {
  try {
    await IntegrityClient.copyHash(hash);
    show("Đã sao chép SHA-256.", "success");
  } catch (error) {
    show(error.message, "error");
  }
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
    const data = await IntegrityClient.request(
      "/health/ready",
      {},
      { timeoutMs: 10000 },
    );
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
    $("refresh").disabled = true;
    $("refresh").textContent = "Đang tải…";
    const data = await api(
      "/api/files?offset=" + offset + "&limit=" + pageSize,
    );
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
        ["Sao chép hash", () => copy(item.sha256)],
      ]) {
        const b = document.createElement("button");
        b.textContent = label;
        b.className = "secondary";
        b.onclick = async () => {
          b.disabled = true;
          b.textContent =
            label === "Verify"
              ? "Đang xác minh…"
              : label === "Tải xuống"
                ? "Đang tải…"
                : "Đang sao chép…";
          try {
            await fn();
          } catch (e) {
            show(e.message, "error");
          } finally {
            b.disabled = false;
            b.textContent = label;
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
  } finally {
    $("refresh").disabled = false;
    $("refresh").textContent = "Làm mới";
  }
}
async function download(item) {
  const blob = await api(
    "/api/files/" + item.id + "/download",
    {},
    { read: "blob", timeoutMs: 120000 },
  );
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = item.filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
async function verify(item) {
  $("verification").hidden = true;
  show("Đang xác minh nội dung: " + item.filename + "…");
  const r = await api(
    "/api/files/" + item.id + "/verify",
    { method: "POST" },
    { timeoutMs: 120000 },
  );
  $("verification").hidden = false;
  $("verification").className =
    "panel verification" + (r.intact ? "" : " changed");
  $("verificationTitle").textContent = r.intact
    ? "TOÀN VẸN"
    : "PHÁT HIỆN THAY ĐỔI";
  $("verificationFile").textContent = item.filename;
  $("expectedHash").textContent = r.expected_sha256;
  $("actualHash").textContent = r.actual_sha256;
  $("verificationSize").textContent =
    "Dung lượng hiện tại / gốc: " +
    r.actual_size +
    " / " +
    r.expected_size +
    " byte";
  $("copyExpected").onclick = () => copy(r.expected_sha256);
  $("copyActual").onclick = () => copy(r.actual_sha256);
  show(
    r.intact
      ? "Đã xác minh: nội dung khớp với lúc tải lên."
      : "Nội dung khác với lúc tải lên. Kiểm tra hai mã băm bên dưới.",
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
  $("upload").textContent = "Đang tải lên…";
  $("file").disabled = true;
  $("uploadForm").setAttribute("aria-busy", "true");
  show("Đang tải lên " + file.name + "…");
  try {
    await api(
      "/api/files?filename=" + encodeURIComponent(file.name),
      {
        method: "POST",
        headers: { "Content-Type": "application/octet-stream" },
        body: file,
      },
      { timeoutMs: 120000 },
    );
    show("Đã lưu tệp và SHA-256: " + file.name, "success");
    $("file").value = "";
    offset = 0;
    await refresh();
  } catch (e) {
    show(
      "Tải lên chưa thành công: " +
        e.message +
        (e.uncertain
          ? " Máy chủ có thể đã nhận tệp. Hãy làm mới danh sách trước khi tải lại."
          : ""),
      "error",
    );
  } finally {
    busy = false;
    $("upload").disabled = false;
    $("upload").textContent = "Tải lên và lưu SHA-256";
    $("file").disabled = false;
    $("uploadForm").setAttribute("aria-busy", "false");
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
  if (!busy && e.dataTransfer.files.length)
    $("file").files = e.dataTransfer.files;
});
health();
refresh();
