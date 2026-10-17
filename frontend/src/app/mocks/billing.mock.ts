import { Invoice, InvoiceStatus } from '../features/billing/models/invoice.model';
import { Sale } from '../features/sales/models/sale.model';
import { SALES_MOCK } from './sales.mock';

/** 1 de cada 9 ventas se registró sin factura electrónica (venta manual). */
const MANUAL_EVERY = 9;
const FIRST_NUMBER = 98;

const addSeconds = (iso: string, seconds: number): string => new Date(new Date(iso).getTime() + seconds * 1000).toISOString();

/** Clave de acceso de 49 dígitos, derivada del número para que sea estable entre cargas. */
function accessKey(n: number): string {
  return `${String(n).padStart(8, '0')}${'0117923456780012001001'}${String(n).padStart(9, '0')}1234567${n % 10}1`.slice(0, 49);
}

function customerFor(sale: Sale, n: number): Invoice['customer'] {
  const isFinalConsumer = sale.customerName === 'Consumidor Final';
  return {
    rucOrCedula: isFinalConsumer ? '9999999999' : `17${String(n * 7919).padStart(8, '0').slice(-8)}001`,
    razonSocial: sale.customerName,
    email: isFinalConsumer ? '' : 'facturacion@cliente.demo',
  };
}

function buildInvoices(): Invoice[] {
  const ordered = [...SALES_MOCK].sort((a, b) => a.date.localeCompare(b.date));
  const invoiced = ordered.filter((_, index) => index % MANUAL_EVERY !== 4);

  const invoices = invoiced.map((sale, index): Invoice => {
    const n = FIRST_NUMBER + index;
    const fromEnd = invoiced.length - 1 - index;
    // Las dos ventas más recientes sirven para ver los estados que no son "autorizada".
    const status: InvoiceStatus = fromEnd === 0 ? 'pendiente' : fromEnd === 1 ? 'rechazada' : 'autorizada';

    const timeline: { status: InvoiceStatus; at: string }[] = [
      { status: 'borrador', at: sale.date },
      { status: 'procesando', at: addSeconds(sale.date, 2) },
      { status: 'pendiente', at: addSeconds(sale.date, 4) },
    ];
    if (status !== 'pendiente') timeline.push({ status, at: addSeconds(sale.date, 7) });

    return {
      id: `inv-${n}`,
      saleId: sale.id,
      numero: `001-001-${String(n).padStart(9, '0')}`,
      claveAcceso: accessKey(n),
      customer: customerFor(sale, n),
      items: sale.items,
      subtotal: sale.subtotal,
      iva: sale.ivaAmount,
      total: sale.total,
      status,
      statusHistory: timeline.map((event) => ({ status: event.status, timestamp: event.at })),
      rejectionReason:
        status === 'rechazada' ? 'El RUC del cliente no consta como registro válido en el SRI (simulado).' : undefined,
      createdAt: sale.date,
      authorizedAt: status === 'autorizada' ? addSeconds(sale.date, 7) : undefined,
      createdBy: sale.createdBy,
    };
  });

  // Más recientes primero, como las muestra el historial.
  return invoices.reverse();
}

export const INVOICES_MOCK: Invoice[] = buildInvoices();
