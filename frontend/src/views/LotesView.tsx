import React, { useState, useEffect } from "react";
import {
  LoteDE,
  FacturaOut,
  listLotes,
  getLoteDetalle,
  enviarLoteAsincrono,
  consultarLoteSifen,
  listFacturas,
} from "../api";

export const LotesView: React.FC = () => {
  const [lotes, setLotes] = useState<LoteDE[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modal para nuevo envío de lote
  const [modalOpen, setModalOpen] = useState(false);
  const [facturasFirmadas, setFacturasFirmadas] = useState<FacturaOut[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [certPassword, setCertPassword] = useState("");
  const [sending, setSending] = useState(false);

  // Detalle de lote seleccionado
  const [selectedLote, setSelectedLote] = useState<LoteDE | null>(null);
  const [loteFacturas, setLoteFacturas] = useState<any[]>([]);
  const [pollingId, setPollingId] = useState<number | null>(null);

  const cargarLotes = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listLotes();
      setLotes(data);
    } catch (err: any) {
      setError(err.message || "Error al cargar lotes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    cargarLotes();
  }, []);

  const abrirModalEnvio = async () => {
    setError(null);
    try {
      const all = await listFacturas();
      // Filtrar facturas firmadas que no hayan sido enviadas aún
      const pendientes = all.filter(
        (f) => f.estado_envio === "firmado" || f.estado_envio === "pendiente"
      );
      setFacturasFirmadas(pendientes);
      setSelectedIds(pendientes.slice(0, 50).map((f) => f.id));
      setModalOpen(true);
    } catch (err: any) {
      setError("Error al cargar facturas disponibles para envío en lote");
    }
  };

  const handleEnviarLote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (selectedIds.length === 0) {
      alert("Seleccione al menos un documento para el lote");
      return;
    }
    setSending(true);
    setError(null);
    setSuccess(null);
    try {
      const res = await enviarLoteAsincrono(selectedIds, certPassword);
      setSuccess(`Lote enviado con éxito. Protocolo: ${res.protocolo || "Encolado"}`);
      setModalOpen(false);
      await cargarLotes();
    } catch (err: any) {
      setError(err.message || "Error al enviar el lote a SIFEN");
    } finally {
      setSending(false);
    }
  };

  const handleConsultarLote = async (loteId: number) => {
    setPollingId(loteId);
    setError(null);
    setSuccess(null);
    try {
      const res = await consultarLoteSifen(loteId);
      setSuccess(`Lote ${loteId}: ${res.mensaje_lote || "Consultado"}`);
      await cargarLotes();
      if (selectedLote && selectedLote.id === loteId) {
        verDetalle(loteId);
      }
    } catch (err: any) {
      setError(err.message || "Error al consultar estado del lote");
    } finally {
      setPollingId(null);
    }
  };

  const verDetalle = async (loteId: number) => {
    try {
      const data = await getLoteDetalle(loteId);
      setSelectedLote(data.lote);
      setLoteFacturas(data.facturas);
    } catch (err: any) {
      setError("Error al cargar detalle del lote");
    }
  };

  return (
    <div className="lotes-view" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div>
          <h2 style={{ margin: 0, color: "#1e293b" }}>📦 Monitor de Lotes Asíncronos SIFEN</h2>
          <p style={{ margin: "4px 0 0 0", color: "#64748b", fontSize: "14px" }}>
            Recepción y consulta asíncrona de lotes de hasta 50 documentos (Normativa Octubre 2024).
          </p>
        </div>
        <div style={{ display: "flex", gap: "10px" }}>
          <button
            onClick={cargarLotes}
            style={{
              background: "#f1f5f9",
              color: "#334155",
              border: "1px solid #cbd5e1",
              padding: "8px 16px",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            🔄 Actualizar
          </button>
          <button
            onClick={abrirModalEnvio}
            style={{
              background: "#2563eb",
              color: "#fff",
              border: "none",
              padding: "8px 16px",
              borderRadius: "6px",
              cursor: "pointer",
              fontWeight: "bold",
            }}
          >
            ➕ Enviar Nuevo Lote
          </button>
        </div>
      </div>

      {error && (
        <div style={{ background: "#fee2e2", color: "#991b1b", padding: "12px", borderRadius: "6px", marginBottom: "15px" }}>
          ❌ {error}
        </div>
      )}

      {success && (
        <div style={{ background: "#dcfce7", color: "#166534", padding: "12px", borderRadius: "6px", marginBottom: "15px" }}>
          ✅ {success}
        </div>
      )}

      {loading ? (
        <p>Cargando lotes...</p>
      ) : lotes.length === 0 ? (
        <div style={{ background: "#fff", padding: "40px", textAlign: "center", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
          <p style={{ color: "#64748b", margin: 0 }}>No se han enviado lotes asíncronos todavía.</p>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: selectedLote ? "1fr 1fr" : "1fr", gap: "20px" }}>
          <div style={{ background: "#fff", borderRadius: "8px", border: "1px solid #e2e8f0", overflow: "hidden" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "14px" }}>
              <thead style={{ background: "#f8fafc", borderBottom: "1px solid #e2e8f0" }}>
                <tr>
                  <th style={{ padding: "12px" }}>ID Lote</th>
                  <th style={{ padding: "12px" }}>Protocolo</th>
                  <th style={{ padding: "12px" }}>Cant. DE</th>
                  <th style={{ padding: "12px" }}>Estado</th>
                  <th style={{ padding: "12px" }}>Fecha</th>
                  <th style={{ padding: "12px" }}>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {lotes.map((l) => (
                  <tr key={l.id} style={{ borderBottom: "1px solid #f1f5f9" }}>
                    <td style={{ padding: "12px", fontWeight: "bold" }}>#{l.id}</td>
                    <td style={{ padding: "12px", fontFamily: "monospace", color: "#2563eb" }}>
                      {l.d_prot_cons_lote || "—"}
                    </td>
                    <td style={{ padding: "12px" }}>{l.cantidad_de} doc(s)</td>
                    <td style={{ padding: "12px" }}>
                      <span
                        style={{
                          display: "inline-block",
                          padding: "4px 8px",
                          borderRadius: "12px",
                          fontSize: "12px",
                          fontWeight: "bold",
                          background:
                            l.estado === "concluido"
                              ? "#dcfce7"
                              : l.estado === "en_procesamiento" || l.estado === "encolado"
                              ? "#fef3c7"
                              : "#fee2e2",
                          color:
                            l.estado === "concluido"
                              ? "#166534"
                              : l.estado === "en_procesamiento" || l.estado === "encolado"
                              ? "#854d0e"
                              : "#991b1b",
                        }}
                      >
                        {l.estado.toUpperCase()}
                      </span>
                    </td>
                    <td style={{ padding: "12px", color: "#64748b" }}>
                      {new Date(l.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: "12px" }}>
                      <button
                        onClick={() => verDetalle(l.id)}
                        style={{
                          background: "#f1f5f9",
                          border: "1px solid #cbd5e1",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          marginRight: "6px",
                          cursor: "pointer",
                        }}
                      >
                        👁️ Ver
                      </button>
                      <button
                        onClick={() => handleConsultarLote(l.id)}
                        disabled={pollingId === l.id}
                        style={{
                          background: "#3b82f6",
                          color: "#fff",
                          border: "none",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          cursor: "pointer",
                        }}
                      >
                        {pollingId === l.id ? "Consultando..." : "🔍 SIFEN"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {selectedLote && (
            <div style={{ background: "#fff", borderRadius: "8px", border: "1px solid #e2e8f0", padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <h3 style={{ margin: 0 }}>Detalle Lote #{selectedLote.id}</h3>
                <button
                  onClick={() => setSelectedLote(null)}
                  style={{ background: "transparent", border: "none", fontSize: "16px", cursor: "pointer" }}
                >
                  ✖
                </button>
              </div>

              <div style={{ marginTop: "15px", fontSize: "14px", color: "#475569" }}>
                <p><strong>Protocolo SIFEN:</strong> {selectedLote.d_prot_cons_lote || "Pendiente"}</p>
                <p><strong>Mensaje SIFEN:</strong> {selectedLote.sifen_msg_res || "Sin respuesta"}</p>
                <p><strong>Última Consulta:</strong> {selectedLote.consultado_at ? new Date(selectedLote.consultado_at).toLocaleString() : "No consultado"}</p>
              </div>

              <h4 style={{ marginTop: "20px", marginBottom: "10px" }}>Documentos en este Lote:</h4>
              <div style={{ maxHeight: "300px", overflowY: "auto" }}>
                {loteFacturas.map((f: any) => (
                  <div
                    key={f.id}
                    style={{
                      background: "#f8fafc",
                      padding: "10px",
                      borderRadius: "6px",
                      border: "1px solid #e2e8f0",
                      marginBottom: "8px",
                      fontSize: "13px",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between" }}>
                      <strong>Factura #{f.numero_documento}</strong>
                      <span style={{ fontWeight: "bold", color: f.estado_envio === "aprobado" ? "#166534" : "#dc2626" }}>
                        {f.estado_envio.toUpperCase()}
                      </span>
                    </div>
                    <div style={{ color: "#64748b", marginTop: "4px" }}>Receptor: {f.receptor_nombre}</div>
                    <div style={{ fontFamily: "monospace", fontSize: "11px", color: "#2563eb", marginTop: "2px" }}>
                      CDC: {f.cdc}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modal Enviar Lote */}
      {modalOpen && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            width: "100vw",
            height: "100vh",
            background: "rgba(0,0,0,0.5)",
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            zIndex: 1000,
          }}
        >
          <div style={{ background: "#fff", borderRadius: "8px", padding: "24px", width: "600px", maxHeight: "80vh", overflowY: "auto" }}>
            <h3>Enviar Documentos en Lote Asíncrono</h3>
            <p style={{ color: "#64748b", fontSize: "14px" }}>
              Seleccione hasta 50 documentos. Se generará el paquete ZIP comprimido Base64 conforme a la norma SIFEN.
            </p>

            <form onSubmit={handleEnviarLote}>
              <div style={{ maxHeight: "250px", overflowY: "auto", border: "1px solid #e2e8f0", borderRadius: "6px", padding: "10px", marginBottom: "15px" }}>
                {facturasFirmadas.length === 0 ? (
                  <p style={{ color: "#64748b" }}>No hay facturas pendientes de envío.</p>
                ) : (
                  facturasFirmadas.map((f) => (
                    <label key={f.id} style={{ display: "flex", alignItems: "center", padding: "6px 0", borderBottom: "1px solid #f1f5f9", cursor: "pointer" }}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(f.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            if (selectedIds.length >= 50) {
                              alert("Máximo 50 documentos por lote");
                              return;
                            }
                            setSelectedIds([...selectedIds, f.id]);
                          } else {
                            setSelectedIds(selectedIds.filter((id) => id !== f.id));
                          }
                        }}
                        style={{ marginRight: "10px" }}
                      />
                      <div style={{ flex: 1, fontSize: "13px" }}>
                        <strong>Doc #{f.numero_documento}</strong> — {f.receptor_nombre} ({f.d_tot_gral_ope.toLocaleString()} Gs.)
                        <div style={{ color: "#64748b", fontSize: "11px", fontFamily: "monospace" }}>CDC: {f.cdc}</div>
                      </div>
                    </label>
                  ))
                )}
              </div>

              <div style={{ marginBottom: "15px" }}>
                <label style={{ display: "block", fontSize: "13px", fontWeight: "bold", marginBottom: "4px" }}>
                  Contraseña Certificado .p12 (Opcional si ya está configurado):
                </label>
                <input
                  type="password"
                  value={certPassword}
                  onChange={(e) => setCertPassword(e.target.value)}
                  placeholder="Contraseña"
                  style={{ width: "100%", padding: "8px", borderRadius: "4px", border: "1px solid #cbd5e1" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  style={{ background: "#f1f5f9", border: "1px solid #cbd5e1", padding: "8px 16px", borderRadius: "6px", cursor: "pointer" }}
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  disabled={sending || selectedIds.length === 0}
                  style={{ background: "#2563eb", color: "#fff", border: "none", padding: "8px 16px", borderRadius: "6px", cursor: "pointer", fontWeight: "bold" }}
                >
                  {sending ? "Empaquetando y Enviando..." : `Enviar ${selectedIds.length} DE(s)`}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
