/* Shared browser/Node helpers. No dependencies or build step required. */
(function (root, factory) {
  const helpers = factory();
  if (typeof module === "object" && module.exports) module.exports = helpers;
  else root.IntegrityClient = helpers;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  class ApiError extends Error {
    constructor(message, status = 0, uncertain = false) {
      super(message);
      this.status = status;
      this.uncertain = uncertain;
    }
  }

  function statusMessage(status) {
    if (status === 401)
      return "API key thiếu hoặc không đúng. Hãy kiểm tra ô API key.";
    if (status === 413) return "Tệp vượt giới hạn dung lượng của máy chủ.";
    if (status === 404) return "Không tìm thấy tệp. Hãy làm mới danh sách.";
    if (status >= 500)
      return "Dịch vụ đang gặp sự cố. Hãy kiểm tra trạng thái và thử lại sau.";
    return "Yêu cầu không thành công (HTTP " + status + ").";
  }

  async function request(url, options = {}, config = {}) {
    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      config.timeoutMs ?? 30000,
    );
    const fetcher = config.fetcher || globalThis.fetch;
    try {
      const response = await fetcher(url, {
        ...options,
        signal: controller.signal,
      });
      if (!response.ok)
        throw new ApiError(statusMessage(response.status), response.status);
      return await (config.read === "blob" ? response.blob() : response.json());
    } catch (error) {
      if (error instanceof ApiError) throw error;
      if (controller.signal.aborted) {
        throw new ApiError(
          "Yêu cầu quá thời gian chờ. Hãy kiểm tra kết nối.",
          0,
          true,
        );
      }
      if (error instanceof SyntaxError)
        throw new ApiError("Máy chủ trả về dữ liệu không hợp lệ.");
      throw new ApiError(
        "Không kết nối được dịch vụ. Hãy kiểm tra mạng hoặc trạng thái máy chủ.",
        0,
        true,
      );
    } finally {
      clearTimeout(timeout);
    }
  }

  async function copyHash(hash, clipboard) {
    if (!/^[a-f0-9]{64}$/i.test(hash)) throw new Error("SHA-256 không hợp lệ.");
    const target = clipboard || globalThis.navigator?.clipboard;
    if (!target?.writeText)
      throw new Error(
        "Trình duyệt không cho phép sao chép. Hãy chọn mã băm và sao chép thủ công.",
      );
    try {
      await target.writeText(hash);
    } catch {
      throw new Error(
        "Không sao chép được. Hãy chọn mã băm và sao chép thủ công.",
      );
    }
  }

  return { ApiError, request, copyHash };
});
