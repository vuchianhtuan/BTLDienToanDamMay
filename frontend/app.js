const $ = (id) => document.getElementById(id);
let offset = 0,
  limit = 0,
  busy = false;
let activeUpload = null;
let listRequest = 0;
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
function errorDetail(status, body) {
  if (status === 401) return "API key thiếu hoặc không đúng. Nhập key rồi làm mới.";
  if (status === 413) return "Tệp vượt giới hạn máy chủ cho phép.";
  if (status === 503) return "Database hoặc storage chưa sẵn sàng. Thử lại sau.";
  try {
    const data = JSON.parse(body);
    if (typeof data.detail === "string") return data.detail;
  } catch {}
  return "Yêu cầu thất bại (HTTP " + status + ").";
}
async function api(url, options = {}) {
  let r;
  try {
    r = await fetch(url, {
      ...options,
      signal: AbortSignal.timeout(120000),
      headers: { ...headers(), ...(options.headers || {}) },
    });
  } catch (e) {
    throw new Error(e.name === "TimeoutError"
      ? "Yêu cầu quá thời gian chờ. Kiểm tra dịch vụ rồi thử lại."
      : "Không kết nối được máy chủ. Kiểm tra kết nối rồi thử lại.");
  }
  if (!r.ok) {
    throw new Error(errorDetail(r.status, await r.text()));
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
    const r = await fetch("/health/ready", { signal: AbortSignal.timeout(10000) });
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
async function refresh(targetOffset = offset) {
  const request = ++listRequest;
  $("files").setAttribute("aria-busy", "true");
  for (const id of ["refresh", "prev", "next"]) $(id).disabled = true;
  $("page").textContent = "Đang tải danh sách…";
  try {
    const data = await (
      await api("/api/files?offset=" + targetOffset + "&limit=" + (pageSize + 1))
    ).json();
    if (request !== listRequest) return;
    // Fetch one extra row to avoid an empty page when the last page is full.
    const hasNext = data.length > pageSize;
    offset = targetOffset;
    $("files").replaceChildren();
    for (const item of data.slice(0, pageSize)) {
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
          b.textContent = label === "Verify" ? "Đang kiểm tra…" : "Đang tải…";
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
    $("next").disabled = !hasNext;
    $("page").textContent = "Trang " + (offset / pageSize + 1);
  } catch (e) {
    if (request !== listRequest) return;
    $("files").replaceChildren();
    const tr = document.createElement("tr");
    cell(tr, "Không tải được danh sách. Kiểm tra kết nối/API key và bấm Làm mới.", "empty").colSpan = 4;
    $("files").append(tr);
    $("page").textContent = "Chưa tải được danh sách";
    show("Không đọc được danh sách: " + e.message, "error");
  } finally {
    if (request === listRequest) {
      $("files").setAttribute("aria-busy", "false");
      $("refresh").disabled = false;
    }
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
function uploadFile(file) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    activeUpload = xhr;
    xhr.open("POST", "/api/files?filename=" + encodeURIComponent(file.name));
    xhr.timeout = 120000;
    xhr.setRequestHeader("Content-Type", "application/octet-stream");
    for (const [name, value] of Object.entries(headers())) xhr.setRequestHeader(name, value);
    xhr.upload.onprogress = (event) => {
      if (!event.lengthComputable) return;
      const percent = Math.round(event.loaded / event.total * 100);
      $("progress").value = percent;
      $("progressText").textContent = percent < 100
        ? "Đã gửi " + percent + "% · " + bytes(event.loaded) + " / " + bytes(event.total)
        : "Đã gửi 100% · Đang chờ máy chủ lưu tệp và SHA-256…";
    };
    xhr.onload = () => xhr.status === 201
      ? resolve()
      : reject(new Error(errorDetail(xhr.status, xhr.responseText)));
    xhr.onerror = () => reject(new Error("Mất kết nối. Kết quả lưu chưa xác định; làm mới danh sách trước khi tải lại."));
    xhr.ontimeout = () => reject(new Error("Quá thời gian chờ. Kết quả lưu chưa xác định; làm mới danh sách trước khi tải lại."));
    xhr.onabort = () => reject(new Error("Đã hủy chờ tải lên. Máy chủ có thể đã nhận tệp; làm mới danh sách để kiểm tra."));
    xhr.send(file);
  });
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
  $("file").disabled = true;
  $("cancelUpload").hidden = false;
  $("uploadProgress").hidden = false;
  $("progress").value = 0;
  $("progressText").textContent = "Đang chuẩn bị tải lên…";
  show("Đang tải lên " + file.name + "…");
  try {
    await uploadFile(file);
    show("Đã lưu tệp và SHA-256: " + file.name, "success");
    $("file").value = "";
    await refresh(0);
  } catch (e) {
    show("Tải lên thất bại: " + e.message, "error");
  } finally {
    busy = false;
    activeUpload = null;
    $("upload").disabled = false;
    $("file").disabled = false;
    $("cancelUpload").hidden = true;
    $("uploadProgress").hidden = true;
  }
};
$("cancelUpload").onclick = () => activeUpload?.abort();
$("refresh").onclick = () => {
  health();
  refresh();
};
$("apiKey").onchange = () => {
  refresh(0);
};
$("prev").onclick = () => {
  refresh(Math.max(0, offset - pageSize));
};
$("next").onclick = () => {
  refresh(offset + pageSize);
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
  if (busy) return;
  if (e.dataTransfer.files.length > 1) {
    show("Mỗi lần tải lên một tệp. Vui lòng chọn lại một tệp.", "error");
    return;
  }
  if (e.dataTransfer.files.length) $("file").files = e.dataTransfer.files;
});
health();
refresh();
