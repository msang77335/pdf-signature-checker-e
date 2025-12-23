
export interface CertificateInfo {
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