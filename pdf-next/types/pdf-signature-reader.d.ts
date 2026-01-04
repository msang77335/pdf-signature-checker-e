export interface SignatureInfo {
  byte_range: string | null;
  coverage: string | null;
  document_unchanged: boolean;
  field_name: string;
  intact: boolean;
  is_expired: boolean;
  is_valid: boolean;
  is_self_signed: boolean;
  cryptographic_signature_valid: boolean;
  cryptographic_message: string | null;
  expiration_status: string | null;
  days_until_expiry: number | null;
  has_timestamp: boolean;
  timestamp_source: string | null;
  key_size: number | null;
  hash_algorithm: string | null;
  issuer: {
    common_name: string;
    country: string;
    organization?: string;
    organizational_unit?: string;
  };
  signer: {
    common_name: string;
    country?: string;
    state_or_province?: string;
    city?: string;
    organization?: string;
    user_id?: string;
  };
  signing_time: string;
  signing_timezone?: string;
  total_size: number | null;
  valid_from: string;
  valid_until: string;
  structure_validation?: {
    is_structure_valid: boolean;
    validation_summary: string;
    warnings: string[];
    formatting_errors: string[];
  };
}

export interface VerifyPDFResponse {
  success: boolean;
  count: number;
  signatures: SignatureInfo[];
}

