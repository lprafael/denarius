import { useState } from "react";
import { syncCompras } from "../api";

interface ComprasViewProps {
  compras: any[];
  refresh: () => Promise<void>;
}

export function ComprasView({ compras, refresh }: ComprasViewProps) {
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function onSyncCompras() {
    setLoading(true);
    setErr("");
    try { 
      await syncCompras(); 
      await refresh(); 
      alert("Sincronizado"); 
    } catch (ex) { 
      setErr(String(ex)); 
    } finally { 
      setLoading(false); 
    }
  }

  return (
    <div className="card wide">
      {err && <div className="alert">{err}</div>}
      <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
        <h2>Facturas Recibidas</h2>
        <button className="secondary" onClick={onSyncCompras} disabled={loading}>Sincronizar SIFEN</button>
      </div>
      <table className="table">
        <thead><tr><th>Fecha</th><th>Emisor</th><th>RUC Emisor</th><th>Total</th><th>IVA</th></tr></thead>
        <tbody>
          {compras.map(c => (
            <tr key={c.id}>
              <td>{new Date(c.fecha_emision).toLocaleDateString()}</td>
              <td>{c.emisor_razon_social}</td>
              <td>{c.emisor_ruc}</td>
              <td>{c.monto_total.toLocaleString()}</td>
              <td>{c.monto_iva.toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
