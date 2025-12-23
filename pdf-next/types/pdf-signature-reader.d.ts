declare module 'pdf-signature-reader' {
  export interface CertInfo {
    clientCertificate: boolean;
    issuedBy: {
      commonName: string;
      organizationName: string;
      countryName: string;
    };
    issuedTo: {
      countryName: string;
      stateOrProvinceName?: string;
      organizationName?: string;
      commonName?: string;
    };
    validityPeriod: {
      notBefore: string;
      notAfter: string;
    };
    pemCertificate: string;
  }

  export function getCertificatesInfoFromPDF(buffer: Buffer): Promise<CertInfo[][]>;
}

export interface SignatureInfo {
  coverage: string;
  document_unchanged: boolean;
  field_name: string;
  intact: boolean;
  is_expired: boolean;
  is_valid: boolean;
  issuer: {
    common_name: string;
    country: string;
    organization?: string;
    organizational_unit?: string;
  };
  signer: {
    common_name: string;
    country: string;
    state_province?: string;
    user_id?: string;
  };
  signing_time: string;
  total_size: number;
  valid_at_signing_time: boolean;
  valid_from: string;
  valid_until: string;
}

export interface VerifyPDFResponse {
  success: boolean;
  count: number;
  signatures: SignatureInfo[];
}