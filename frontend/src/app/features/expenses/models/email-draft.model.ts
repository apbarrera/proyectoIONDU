export type EmailDraftStatus = 'pendiente' | 'convertido' | 'descartado';

export interface EmailExpenseDraft {
  id: string;
  receivedAt: string;
  fromAddress: string;
  subjectRaw: string;
  parsedProviderName: string;
  parsedProviderRuc: string;
  parsedAmount: number;
  parsedDate: string;
  parsedCategory: string;
  confidence: number;
  status: EmailDraftStatus;
}
