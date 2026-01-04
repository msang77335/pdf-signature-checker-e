'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { type VerifyPDFResponse } from '@/types/pdf-signature-reader';
import * as iconv from 'iconv-lite';
import { Building, Calendar, CheckCircle, FileText, HelpCircle, RotateCcw, Shield, Upload, User, XCircle } from 'lucide-react';
import { useEffect, useState } from 'react';

export default function PDFSignatureChecker() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerifyPDFResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [openItems, setOpenItems] = useState<number[]>([]);
  const [showTooltip, setShowTooltip] = useState<string | null>(null);
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  const handleReset = () => {
    setFile(null);
    setResult(null);
    setError(null);
    setOpenItems([]);
  };

  const validateAndSetFile = (selectedFile: File | null) => {
    if (selectedFile?.type === 'application/pdf') {
      setFile(selectedFile);
      setResult(null);
      setError(null);
    } else {
      setError('Vui lòng chọn file PDF hợp lệ');
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    validateAndSetFile(selectedFile || null);
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files?.[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleCheck = async () => {
    if (!file) return;

    setLoading(true);
    setError(null);

    try {
      const arrayBuffer = await file.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      const response = await fetch('/api/check-signature', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/octet-stream',
        },
        body: buffer,
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Lỗi kiểm tra chữ ký');
      }

      const data: VerifyPDFResponse = await response.json();
      console.log(data, 'data received from API');
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Có lỗi xảy ra');
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (date: string) => {
    try {
      const d = new Date(date);
      // Use consistent formatting to avoid hydration mismatch
      const year = d.getFullYear();
      const month = String(d.getMonth() + 1).padStart(2, '0');
      const day = String(d.getDate()).padStart(2, '0');
      const hours = String(d.getHours()).padStart(2, '0');
      const minutes = String(d.getMinutes()).padStart(2, '0');

      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch {
      return date;
    }
  };

  const cleanVietnameseText = (text: string | null | undefined): string => {
    if (!text) return 'N/A';

    try {
      // Try to detect if this is a double-encoded text by checking for common patterns
      if (text.includes('Ã') || text.includes('Æ') || text.includes('áº')) {
        // This looks like UTF-8 bytes being interpreted as ISO-8859-1
        // First encode as iso-8859-1, then decode as utf-8
        const buffer = Buffer.from(text, 'binary');
        const decoded = iconv.decode(buffer, 'utf8');

        return decoded;
      }

      // If no encoding issues detected, return as-is
      return text.trim();
    } catch (error) {
      console.warn('Failed to decode text:', error);
      return text;
    }
  };

  const getTimestampSourceLabel = (source: string | null | undefined): string => {
    if (!source) return 'N/A';
    if (source.includes('not TSA')) {
      return 'Máy tính của người ký';
    }
    return 'Máy chủ xác minh độc lập (TSA)';
  };

  const toggleItem = (index: number) => {
    setOpenItems(prev =>
      prev.includes(index)
        ? prev.filter(i => i !== index)
        : [...prev, index]
    );
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 p-4">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-gray-900">PDF Signature Checker</h1>
          <p className="text-lg text-gray-600">Xác thực chữ ký số và thông tin chứng chỉ kỹ thuật số</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload PDF File
            </CardTitle>
            <CardDescription>
              Tải lên file PDF để xác thực chữ ký điện tử và kiểm tra thông tin chứng chỉ
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <span className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">File PDF</span>
              <div className="relative">
                <input
                  id="pdf-file"
                  type="file"
                  accept=".pdf"
                  onChange={handleFileChange}
                  disabled={loading}
                  className="absolute inset-0 w-full h-full opacity-0 z-10 cursor-pointer"
                />
                <label
                  htmlFor="pdf-file"
                  className={`block w-full border-2 border-dashed rounded-lg p-6 transition-colors ${dragActive
                      ? 'border-blue-400 bg-blue-50'
                      : 'border-gray-300 hover:border-gray-400'
                    } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  onDragEnter={handleDrag}
                  onDragLeave={handleDrag}
                  onDragOver={handleDrag}
                  onDrop={handleDrop}
                >
                  <div className="text-center pointer-events-none">
                    <Upload className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                    <div className="space-y-2">
                      <p className="text-lg font-medium text-gray-900">
                        {dragActive ? 'Thả file PDF vào đây' : 'Kéo thả file PDF vào đây'}
                      </p>
                      <p className="text-sm text-gray-500">
                        hoặc <span className="text-blue-600 font-medium">chọn file</span> từ máy tính
                      </p>
                    </div>
                  </div>
                </label>
              </div>
            </div>

            {file && (
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <FileText className="h-4 w-4" />
                <span>{file.name} ({(file.size / 1024 / 1024).toFixed(2)} MB)</span>
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <XCircle className="h-4 w-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button
              onClick={handleCheck}
              disabled={!file || loading}
              className="w-full"
            >
              {loading ? 'Đang kiểm tra...' : 'Kiểm tra chữ ký'}
            </Button>
          </CardContent>
        </Card>

        {result?.success && result.signatures.length === 0 && (
          <Alert className="bg-amber-50 border-amber-300">
            <AlertDescription className="text-amber-800 font-medium">
              ⚠️ File PDF không chứa chữ ký số. Vui lòng kiểm tra file khác.
            </AlertDescription>
          </Alert>
        )}

        {result?.success && result.signatures.length > 0 && (
          <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle className="h-5 w-5 text-green-600" />
                Kết quả kiểm tra chữ ký ({result.count} chữ ký)
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.signatures.map((signature, index) => {
                const isOpen = openItems.includes(index);
                const signatureKey = `${signature.field_name}-${index}`;

                return (
                  <Collapsible key={signatureKey} className="border border-gray-200 rounded-xl overflow-hidden transition-all duration-200 hover:shadow-sm">
                    <CollapsibleTrigger
                      isOpen={isOpen}
                      onClick={() => toggleItem(index)}
                      className="flex items-center justify-between w-full p-4 hover:bg-gray-50 transition-colors duration-200 text-left focus:outline-none focus:bg-gray-100"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <span className="font-medium">Chữ ký #{index + 1}</span>
                          {signature.is_valid && signature.cryptographic_signature_valid && !signature.is_expired ? (
                            <span className="text-emerald-700 font-medium">Hợp lệ & Còn hiệu lực</span>
                          ) : (
                            <>
                              <span className={signature.is_valid && signature.cryptographic_signature_valid ? "text-blue-700 font-medium" : "text-rose-700 font-medium"}>
                                {(signature.is_valid && signature.cryptographic_signature_valid) ? 'Hợp lệ' : 'Không hợp lệ'}
                              </span>
                              {signature.is_expired && (
                                <span className="text-orange-700 font-medium">• Đã hết hạn</span>
                              )}
                            </>
                          )}
                        </div>
                        <div className="text-sm text-gray-600">
                          {signature.signer?.common_name ? cleanVietnameseText(signature.signer.common_name) : 'Không xác định'}
                        </div>
                      </div>
                    </CollapsibleTrigger>
                    <CollapsibleContent isOpen={isOpen} className="border-t bg-gray-50">
                      <div
                        id={`signature-${index}`}
                        className="p-4 space-y-4"
                      >
                        <div className="grid gap-4">
                          <div className="space-y-2">
                            <h4 className="font-semibold flex items-center gap-2">
                              <Shield className="h-4 w-4" />
                              Tình trạng xác thực
                            </h4>
                            <div className="bg-white p-3 rounded-lg space-y-2">
                              {
                                signature.valid_from && signature.valid_until && (
                                  <div className="flex gap-2 text-sm">
                                    <span className="font-medium min-w-44">Tài liệu đã ký:</span>
                                    <span className={signature.document_unchanged ? "text-emerald-700 font-medium" : "text-rose-700 font-medium"}>
                                      {signature.document_unchanged ? 'Không bị thay đổi' : 'Đã bị thay đổi'}
                                    </span>
                                  </div>
                                )
                              }
                              <div className="flex gap-2 text-sm">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium min-w-44">Chữ ký:</span>
                                  <span className={signature.cryptographic_signature_valid && signature.is_valid ? "text-emerald-700 font-medium" : "text-rose-700 font-medium"}>
                                    {signature.cryptographic_signature_valid && signature.is_valid ? 'Hợp lệ' : 'Không hợp lệ'}
                                  </span>
                                  {!(signature.cryptographic_signature_valid && signature.is_valid) && isMounted && (
                                    <div className="relative flex items-center" suppressHydrationWarning>
                                      <button
                                        onMouseEnter={() => setShowTooltip(`sig-${index}`)}
                                        onMouseLeave={() => setShowTooltip(null)}
                                        className="text-gray-400 hover:text-gray-600 transition-colors"
                                      >
                                        <HelpCircle className="h-4 w-4" />
                                      </button>
                                      {showTooltip === `sig-${index}` && (
                                        <div className="absolute top-full left-0 mt-2 p-3 bg-gray-800 text-white text-xs rounded-lg whitespace-nowrap z-10 shadow-lg">
                                          <div className="mb-1">
                                            <span className="font-semibold">Chi tiết xác minh:</span>
                                          </div>
                                          <div className="flex flex-col gap-1">
                                            <div>
                                              <span>Còn hiệu lực lúc ký: </span>
                                              <span className={signature.is_valid ? "text-emerald-300" : "text-rose-300"}>
                                                {signature.is_valid ? '✓ Có' : '✗ Không'}
                                              </span>
                                            </div>
                                            <div>
                                              <span>Xác minh chữ ký: </span>
                                              <span className={signature.cryptographic_signature_valid ? "text-emerald-300" : "text-rose-300"}>
                                                {signature.cryptographic_signature_valid ? '✓ Có' : '✗ Không'}
                                              </span>
                                            </div>
                                          </div>
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              </div>
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-44">Đã ký lúc:</span>
                                <span className="text-gray-700">{formatDate(signature.signing_time)}</span>
                              </div>
                              {
                                signature.has_timestamp && (
                                  <div className="flex gap-2 text-sm">
                                    <span className="font-medium min-w-44">Nguồn thời gian:</span>
                                    <span className="text-gray-700">
                                      {getTimestampSourceLabel(signature.timestamp_source)}
                                    </span>
                                  </div>
                                )
                              }
                            </div>
                          </div>

                          <div className="space-y-2">
                            <h4 className="font-semibold flex items-center gap-2">
                              <User className="h-4 w-4" />
                              Người ký
                            </h4>
                            <div className="bg-white p-3 rounded-lg space-y-2">
                              {signature.signer?.common_name && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Tên:</span>
                                  <span className="text-gray-700">{cleanVietnameseText(signature.signer.common_name)}</span>
                                </div>
                              )}
                              {signature.signer?.country && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Quốc gia:</span>
                                  <span className="text-gray-700">{signature.signer.country}</span>
                                </div>
                              )}
                              {signature.signer?.state_or_province && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Tỉnh/Thành phố:</span>
                                  <span className="text-gray-700">{cleanVietnameseText(signature.signer.state_or_province)}</span>
                                </div>
                              )}
                              {signature.signer?.user_id && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Mã số:</span>
                                  <span className="text-gray-700">{signature.signer.user_id}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          {
                            signature.issuer && (
                              <div className="space-y-2">
                                <h4 className="font-semibold flex items-center gap-2">
                                  <Building className="h-4 w-4" />
                                  Nhà phát hành (CA)
                                </h4>
                                <div className="bg-white p-3 rounded-lg space-y-2">
                                  {signature.is_self_signed && (
                                    <div className="flex gap-2 text-sm p-2 rounded bg-yellow-50 border-l-4 border-yellow-400">
                                      <span className="text-yellow-700 font-medium">⚠️ Chứng chỉ tự ký - Không được xác thực bởi cơ quan cấp</span>
                                    </div>
                                  )}
                                  {signature.issuer?.common_name && (
                                    <div className="flex gap-2 text-sm">
                                      <span className="font-medium min-w-32">Tên CA:</span>
                                      <span className="text-gray-700">{cleanVietnameseText(signature.issuer.common_name)}</span>
                                    </div>
                                  )}
                                  {signature.issuer?.organization && (
                                    <div className="flex gap-2 text-sm">
                                      <span className="font-medium min-w-32">Tổ chức:</span>
                                      <span className="text-gray-700">{cleanVietnameseText(signature.issuer.organization)}</span>
                                    </div>
                                  )}
                                  {signature.issuer?.organizational_unit && (
                                    <div className="flex gap-2 text-sm">
                                      <span className="font-medium min-w-32">Đơn vị:</span>
                                      <span className="text-gray-700">{cleanVietnameseText(signature.issuer.organizational_unit)}</span>
                                    </div>
                                  )}
                                  {signature.issuer?.country && (
                                    <div className="flex gap-2 text-sm">
                                      <span className="font-medium min-w-32">Quốc gia:</span>
                                      <span className="text-gray-700">{signature.issuer.country}</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )
                          }

                          {
                            signature.valid_from && signature.valid_until && (
                              <div className="space-y-2">
                                <h4 className="font-semibold flex items-center gap-2">
                                  <Calendar className="h-4 w-4" />
                                  Thời gian & Hiệu lực
                                </h4>
                                <div className="bg-white p-3 rounded-lg space-y-2">
                                  <div className="flex gap-2 text-sm">
                                    <span className="font-medium min-w-36">Thời hạn sử dụng:</span>
                                    <div className="flex flex-col gap-1">
                                      <span className="text-gray-700">Từ {formatDate(signature.valid_from)}</span>
                                      <span className="text-gray-700">Đến {formatDate(signature.valid_until)}</span>
                                    </div>
                                  </div>
                                  <div className="flex gap-2 text-sm">
                                    <span className="font-medium min-w-36">Tình trạng hiện tại:</span>
                                    <span className={signature.is_expired ? "text-orange-700 font-medium" : "text-emerald-700 font-medium"}>
                                      {signature.is_expired ? 'Đã hết hạn' : 'Còn hiệu lực'}
                                    </span>
                                  </div>
                                </div>
                              </div>
                            )
                          }
                        </div>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              })}
            </CardContent>
          </Card>

          <Alert className="bg-green-50 border-green-300 shadow-sm">
            <Shield className="h-5 w-5 text-green-600" />
            <AlertDescription className="text-green-800">
              <div className="space-y-2">
                <p className="font-semibold">Cam kết bảo mật dữ liệu</p>
                <p className="text-sm">
                  Chúng tôi cam kết rằng file PDF của bạn sẽ <span className="font-medium">không được lưu trữ hoặc sử dụng cho bất kỳ mục đích nào</span> sau khi kiểm tra chữ ký. Tất cả các xử lý diễn ra trên máy chủ của chúng tôi và dữ liệu sẽ bị xóa ngay sau khi hoàn thành.
                </p>
              </div>
            </AlertDescription>
          </Alert>
          </>
        )}

        {/* Floating Check Another File Button */}
        {result?.success && result.signatures.length > 0 && (
          <button
            onClick={handleReset}
            className="fixed bottom-6 right-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full p-4 shadow-lg transition-all duration-200 hover:shadow-xl flex items-center gap-2"
            title="Kiểm tra file khác"
          >
            <RotateCcw className="h-5 w-5" />
            <span className="hidden sm:inline text-sm font-medium">File khác</span>
          </button>
        )}
      </div>
    </div>
  );
}