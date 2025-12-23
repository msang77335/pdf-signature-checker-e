'use client';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { type VerifyPDFResponse } from '@/types/pdf-signature-reader';
import * as iconv from 'iconv-lite';
import { Building, Calendar, CheckCircle, FileText, Shield, Upload, User, XCircle } from 'lucide-react';
import { useState } from 'react';

export default function PDFSignatureChecker() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<VerifyPDFResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [openItems, setOpenItems] = useState<number[]>([]);

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
    return new Date(date).toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const cleanVietnameseText = (text: string): string => {
    if (!text) return text;
    
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

  const formatCoverage = (coverage: string): string => {
    const coverageMap: { [key: string]: string } = {
      'SignatureCoverageLevel.ENTIRE_FILE': 'Toàn bộ tài liệu',
      'SignatureCoverageLevel.ENTIRE_REVISION': 'Toàn bộ phiên bản hiện tại',
      'ENTIRE_FILE': 'Toàn bộ tài liệu',
      'ENTIRE_REVISION': 'Toàn bộ phiên bản hiện tại',
    };
    return coverageMap[coverage] || coverage.replace('SignatureCoverageLevel.', '');
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
          <p className="text-lg text-gray-600">Kiểm tra chữ ký số trong file PDF</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Upload className="h-5 w-5" />
              Upload PDF File
            </CardTitle>
            <CardDescription>
              Chọn file PDF có chữ ký số để kiểm tra thông tin certificate
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
                  className={`block w-full border-2 border-dashed rounded-lg p-6 transition-colors ${
                    dragActive
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

        {result?.success && result.signatures.length > 0 && (
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
                          {signature.is_valid && !signature.is_expired ? (
                            <span className="text-emerald-700 font-medium">Hợp lệ & Còn hiệu lực</span>
                          ) : (
                            <>
                              <span className={signature.is_valid ? "text-blue-700 font-medium" : "text-rose-700 font-medium"}>
                                {signature.is_valid ? 'Hợp lệ' : 'Không hợp lệ'}
                              </span>
                              {signature.is_expired && (
                                <span className="text-orange-700 font-medium">• Đã hết hạn</span>
                              )}
                            </>
                          )}
                        </div>
                        <div className="text-sm text-gray-600">
                          {cleanVietnameseText(signature.signer.common_name)}
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
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-44">Trạng thái chữ ký:</span>
                                <span className={signature.is_valid ? "text-blue-700 font-medium" : "text-rose-700 font-medium"}>
                                  {signature.is_valid ? 'Hợp lệ' : 'Không hợp lệ'}
                                </span>
                              </div>
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-44">Tài liệu đã ký:</span>
                                <span className={signature.document_unchanged ? "text-emerald-700 font-medium" : "text-rose-700 font-medium"}>
                                  {signature.document_unchanged ? 'Không bị thay đổi' : 'Đã bị thay đổi'}
                                </span>
                              </div>
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-44">Chữ ký:</span>
                                <span className={signature.valid_at_signing_time ? "text-emerald-700 font-medium" : "text-rose-700 font-medium"}>
                                  {signature.valid_at_signing_time ? 'Hợp lệ tại thời điểm ký' : 'Không hợp lệ tại thời điểm ký'}
                                </span>
                              </div>
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-44">Phạm vi bảo vệ:</span>
                                <span className="text-gray-700">{formatCoverage(signature.coverage)}</span>
                              </div>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <h4 className="font-semibold flex items-center gap-2">
                              <User className="h-4 w-4" />
                              Người ký
                            </h4>
                            <div className="bg-white p-3 rounded-lg space-y-2">
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-32">Tên:</span>
                                <span className="text-gray-700">{cleanVietnameseText(signature.signer.common_name)}</span>
                              </div>
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-32">Quốc gia:</span>
                                <span className="text-gray-700">{signature.signer.country}</span>
                              </div>
                              {signature.signer.state_province && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Tỉnh/Thành phố:</span>
                                  <span className="text-gray-700">{cleanVietnameseText(signature.signer.state_province)}</span>
                                </div>
                              )}
                              {signature.signer.user_id && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Mã số:</span>
                                  <span className="text-gray-700">{signature.signer.user_id}</span>
                                </div>
                              )}
                            </div>
                          </div>

                          <div className="space-y-2">
                            <h4 className="font-semibold flex items-center gap-2">
                              <Building className="h-4 w-4" />
                              Nhà phát hành (CA)
                            </h4>
                            <div className="bg-white p-3 rounded-lg space-y-2">
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-32">Tên CA:</span>
                                <span className="text-gray-700">{cleanVietnameseText(signature.issuer.common_name)}</span>
                              </div>
                              {signature.issuer.organization && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Tổ chức:</span>
                                  <span className="text-gray-700">{cleanVietnameseText(signature.issuer.organization)}</span>
                                </div>
                              )}
                              {signature.issuer.organizational_unit && (
                                <div className="flex gap-2 text-sm">
                                  <span className="font-medium min-w-32">Đơn vị:</span>
                                  <span className="text-gray-700">{cleanVietnameseText(signature.issuer.organizational_unit)}</span>
                                </div>
                              )}
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-32">Quốc gia:</span>
                                <span className="text-gray-700">{signature.issuer.country}</span>
                              </div>
                            </div>
                          </div>

                          <div className="space-y-2">
                            <h4 className="font-semibold flex items-center gap-2">
                              <Calendar className="h-4 w-4" />
                              Thời gian & Hiệu lực
                            </h4>
                            <div className="bg-white p-3 rounded-lg space-y-2">
                              <div className="flex gap-2 text-sm">
                                <span className="font-medium min-w-36">Đã ký lúc:</span>
                                <span className="text-gray-700">{formatDate(signature.signing_time)}</span>
                              </div>
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
                        </div>
                      </div>
                    </CollapsibleContent>
                  </Collapsible>
                );
              })}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}