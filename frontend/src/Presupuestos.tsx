import { useState, useEffect, useRef } from "react";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { 
    listPresupuestos, 
    createPresupuesto, 
    enviarPresupuesto, 
    autocompleteGrupos, 
    autocompleteConceptos, 
    getLogo, 
    uploadLogo,
    getPresupuestoConfig,
    updatePresupuestoConfig,
    getClienteByRuc,
    upsertCliente,
    restoreAccessToken,
    updatePresupuesto
} from "./api";

function numeroALetras(num: number): string {
    const unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"];
    const decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"];
    const especiales = ["ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"];
    const centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"];

    if (num === 0) return "CERO";
    if (num < 0) return "MENOS " + numeroALetras(Math.abs(num));

    let str = "";
    if (num >= 1000000) {
        const millon = Math.floor(num / 1000000);
        if (millon === 1) str += "UN MILLON ";
        else str += numeroALetras(millon) + " MILLONES ";
        num %= 1000000;
    }
    if (num >= 1000) {
        const mil = Math.floor(num / 1000);
        if (mil === 1) str += "MIL ";
        else str += numeroALetras(mil) + " MIL ";
        num %= 1000;
    }
    if (num >= 100) {
        if (num === 100) { str += "CIEN "; num = 0; }
        else { str += centenas[Math.floor(num / 100)] + " "; num %= 100; }
    }
    if (num >= 10 && num <= 19) {
        if (num === 10) str += "DIEZ ";
        else str += especiales[num - 11] + " ";
        num = 0;
    } else if (num >= 20) {
        if (num === 20) { str += "VEINTE "; num = 0; }
        else if (num < 30) { str += "VEINTI" + unidades[num - 20] + " "; num = 0; }
        else {
            str += decenas[Math.floor(num / 10)] + " ";
            num %= 10;
            if (num > 0) str += "Y ";
        }
    }
    if (num > 0) {
        str += unidades[num] + " ";
    }
    return str.trim();
}

    export function PresupuestosView({ empresaNombre, onAddCliente }: { empresaNombre: string; onAddCliente?: () => void }) {
    const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);
    const [presupuestos, setPresupuestos] = useState<any[]>([]);
const [view, setView] = useState<"list" | "create">("list");
const [editingId, setEditingId] = useState<number | null>(null);
const [logoUrl, setLogoUrl] = useState<string>("");
    
    // Auto-complete data
    const [sugGrupos, setSugGrupos] = useState<string[]>([]);
    const [sugConceptos, setSugConceptos] = useState<any[]>([]);

    // Form state
    const [clienteNombre, setClienteNombre] = useState("");
    const [clienteRuc, setClienteRuc] = useState("");
  const [clienteEmail, setClienteEmail] = useState("");
  const [clienteTelefono, setClienteTelefono] = useState("");
  const [clienteDir, setClienteDir] = useState("");
  const [clienteEncontrado, setClienteEncontrado] = useState<any>(null);
  const [showClienteModal, setShowClienteModal] = useState(false);
  const [loading, setLoading] = useState(false);
    const [numero, setNumero] = useState<number | "">("");
    const [validezDias, setValidezDias] = useState<number>(15);
    
    // Texto pie editable - se carga desde la config de la empresa
    const [textoPie, setTextoPie] = useState("");
    const [textoPieDefault, setTextoPieDefault] = useState("");
    const [editandoDefault, setEditandoDefault] = useState(false);
    const [textoPieDefaultEdit, setTextoPieDefaultEdit] = useState("");
    
    const [grupos, setGrupos] = useState<any[]>([
        { id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0, tasa_iva: 10 }] }
    ]);

    const printRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        const init = async () => {
            await restoreAccessToken();
            if (view === "list") await loadData();
            await loadConfig();
        };
        init();
    }, [view]);

    async function loadData() {
        try {
            setPresupuestos(await listPresupuestos());
        } catch(e) { console.error(e); }
    }

    async function loadConfig() {
        try {
            const logo = await getLogo();
            setLogoUrl(logo.logo_url);
            setSugGrupos(await autocompleteGrupos());
            setSugConceptos(await autocompleteConceptos());
            const config = await getPresupuestoConfig();
            setTextoPieDefault(config.texto_pie_presupuesto);
            // Al crear un nuevo presupuesto, iniciar con el texto por defecto
            if (!textoPie) setTextoPie(config.texto_pie_presupuesto);
        } catch(e) { console.error(e); }
    }

    async function handleLogoUpload(e: React.ChangeEvent<HTMLInputElement>) {
        if (!e.target.files?.length) return;
        try {
            const res = await uploadLogo(e.target.files[0]);
            setLogoUrl(res.logo_url);
            alert("Logo actualizado");
        } catch(err) {
            alert("Error subiendo logo");
        }
    }

    async function guardarTextoPieDefault() {
        try {
            await updatePresupuestoConfig({ texto_pie_presupuesto: textoPieDefaultEdit });
            setTextoPieDefault(textoPieDefaultEdit);
            setEditandoDefault(false);
            alert("Texto por defecto actualizado");
        } catch(e) {
            alert("Error al guardar");
        }
    }

    function calcularTotalesIva() {
        let exentas = 0;
        let iva5 = 0;
        let iva10 = 0;
        
        for (const g of grupos) {
            for (const c of g.conceptos) {
                const subt = c.cantidad * c.precio_unitario;
                const sign = g.es_suma ? 1 : -1;
                const val = subt * sign;
                
                if (c.tasa_iva === 10) iva10 += val;
                else if (c.tasa_iva === 5) iva5 += val;
                else exentas += val;
            }
        }
        
        const total = exentas + iva5 + iva10;
        const liq5 = Math.round(iva5 / 21);
        const liq10 = Math.round(iva10 / 11);
        
        return { exentas, iva5, iva10, total, liq5, liq10, liqTotal: liq5 + liq10 };
    }

    function calcularTotal() {
        return calcularTotalesIva().total;
    }

    async function generatePdfBase64(): Promise<string> {
        if (!printRef.current) return "";
        const hiddenElements = Array.from(printRef.current.querySelectorAll<HTMLElement>(".no-print"));
        const originalDisplays = hiddenElements.map(el => el.style.display);
        try {
            hiddenElements.forEach(el => { el.style.display = "none"; });
            const canvas = await html2canvas(printRef.current, { scale: 3, useCORS: true, logging: false, allowTaint: true });
            const imgData = canvas.toDataURL("image/png");
            const pdf = new jsPDF("p", "mm", "a4");
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
            pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
            const pdfDataUri = pdf.output("datauristring");
            return pdfDataUri.split(",")[1];
        } finally {
            hiddenElements.forEach((el, index) => { el.style.display = originalDisplays[index]; });
        }
    }

    async function downloadPdf() {
        if (!printRef.current) return;
        setIsGeneratingPdf(true);
        const hiddenElements = Array.from(printRef.current.querySelectorAll<HTMLElement>(".no-print"));
        const originalDisplays = hiddenElements.map(el => el.style.display);
        try {
            hiddenElements.forEach(el => { el.style.display = "none"; });
            const canvas = await html2canvas(printRef.current, { scale: 3, useCORS: true, logging: false, allowTaint: true });
            const imgData = canvas.toDataURL("image/png");
            const pdf = new jsPDF("p", "mm", "a4");
            const pdfWidth = pdf.internal.pageSize.getWidth();
            const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
            pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
            pdf.save(`Presupuesto_${numero || 'Nuevo'}.pdf`);
        } catch(e) {
            console.error("Error generating PDF:", e);
            alert("Hubo un error al generar el PDF.");
        } finally {
            hiddenElements.forEach((el, index) => { el.style.display = originalDisplays[index]; });
            setIsGeneratingPdf(false);
        }
    }

    const onRucBlur = async (ruc: string) => {
    if (!ruc) return;
    try {
        const existing = await getClienteByRuc(ruc);
        if (existing) {
            setClienteNombre(existing.razon_social || "");
            setClienteEmail(existing.email || "");
            setClienteTelefono(existing.telefono || "");
            setClienteDir(existing.direccion || "");
            setClienteEncontrado({ _is_new_sifen: false });
        } else {
            setClienteEncontrado({ _is_new_sifen: true });
        }
    } catch (e) {
        console.error(e);
    }
};

    async function onSave(enviar: boolean) {
        try {
            if (!clienteNombre) return alert("Ingrese el nombre del cliente");
            // Validar cliente por RUC y crear si no existe
            if (clienteRuc) {
                const existing = await getClienteByRuc(clienteRuc);
                if (!existing) {
                    await upsertCliente({
                        ruc_con_dv: clienteRuc,
                        razon_social: clienteNombre,
                        email: clienteEmail,
                        telefono: clienteTelefono,
                        direccion: "",
                    });
                }
            }
            const payload = {
                numero: numero || undefined,
                cliente_nombre: clienteNombre,
                cliente_email: clienteEmail,
                cliente_telefono: clienteTelefono,
                cliente_ruc: clienteRuc,
                validez_dias: validezDias,
                texto_pie: textoPie,
                grupos: grupos.map((g, i) => ({
                    nombre: g.nombre,
                    es_suma: g.es_suma,
                    orden: i,
                    conceptos: g.conceptos.map((c: any, j: number) => ({
                        descripcion: c.descripcion,
                        cantidad: Number(c.cantidad),
                        precio_unitario: Number(c.precio_unitario),
                        tasa_iva: Number(c.tasa_iva ?? 10),
                        orden: j
                    }))
                }))
            };

            const saved = editingId 
                ? await updatePresupuesto(editingId, payload) 
                : await createPresupuesto(payload);
            
            // Retrieve admin email (placeholder, replace with actual admin email retrieval)
            const adminEmail = "admin@example.com"; 

            if (enviar && clienteEmail) {
                const base64 = await generatePdfBase64();
                await enviarPresupuesto(saved.id, {
                    pdf_base64: base64,
                    destinatario: clienteEmail,
                    asunto: `Presupuesto Nº ${saved.numero} - ${empresaNombre}`,
                    mensaje: `Estimado/a ${clienteNombre},\n\nAdjuntamos el presupuesto solicitado.\n\nSaludos,\n${empresaNombre}`,
                    cc: adminEmail // CC to admin
                });
                alert("Presupuesto guardado y enviado por correo!");
            } else {
                alert("Presupuesto guardado" + (!clienteEmail && enviar ? " (no se envió correo porque no se indicó email)" : ""));
            }
            setView("list");
            
        } catch(e: any) {
            alert("Error: " + e.message);
        }
    }

    // ---------- VISTA LISTA ----------
    if (view === "list") {
        return (
            <div className="card wide">
                <div className="h-stack" style={{justifyContent: 'space-between', marginBottom:'1rem'}}>
                    <h2>📋 Presupuestos</h2>
<button className="primary" onClick={() => {
    // Load the most recent presupuesto as a template
    if (presupuestos && presupuestos.length > 0) {
        const recent = presupuestos.reduce((prev, curr) => {
            const prevDate = new Date(prev.fecha);
            const currDate = new Date(curr.fecha);
            return currDate > prevDate ? curr : prev;
        }, presupuestos[0]);
        // Populate fields from the recent presupuesto for groups and template only
        setNumero(""); // Reset the number so it auto-generates
        setClienteNombre("");
        setClienteEmail("");
        setClienteTelefono("");
        setClienteRuc("");
        setValidezDias(recent.validez_dias ?? 15);
        setTextoPie(recent.texto_pie ?? textoPieDefault);
        setGrupos(
            recent.grupos?.map((g: any) => ({
                id: Date.now() + Math.random(),
                nombre: g.nombre,
                es_suma: g.es_suma,
                conceptos: g.conceptos?.map((c: any) => ({
                    id: Date.now() + Math.random(),
                    descripcion: c.descripcion,
                    cantidad: c.cantidad,
                    precio_unitario: c.precio_unitario,
                    tasa_iva: c.tasa_iva ?? 10,
                })) ?? []
            })) ?? [{ id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now() + 1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0, tasa_iva: 10 }] }]
        );
    } else {
        // No previous presupuestos, start with defaults
        setTextoPie(textoPieDefault);
        setClienteNombre("");
        setClienteEmail("");
        setClienteTelefono("");
        setClienteRuc("");
        setNumero("");
        setGrupos([{ id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now() + 1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0, tasa_iva: 10 }] }]);
    }
    setEditingId(null);
    setView("create");
}}>+ Nuevo Presupuesto</button>
                </div>

                {/* Configuración rápida */}
                <div style={{marginBottom: '1.5rem', padding:'1rem', borderRadius:'8px', backgroundColor:'rgba(255,255,255,0.05)', border:'1px solid rgba(255,255,255,0.1)'}}>
                    <div className="h-stack" style={{gap:'1rem', alignItems:'center', flexWrap:'wrap'}}>
                        <div>
                            <label className="hint" style={{fontSize:'12px'}}>Logo de la Empresa</label>
                            <div className="h-stack" style={{gap:'10px', alignItems:'center', marginTop:'4px'}}>
                                <input type="file" accept="image/*" onChange={handleLogoUpload} style={{fontSize:'12px'}} />
                                {logoUrl && <img src={logoUrl} alt="Logo" style={{height: '36px', objectFit:'contain', borderRadius:'4px'}} />}
                            </div>
                        </div>
                    </div>
                    
                    <div style={{marginTop:'1rem'}}>
                        <label className="hint" style={{fontSize:'12px'}}>Texto al Pie (por defecto para nuevos presupuestos)</label>
                        {!editandoDefault ? (
                            <div className="h-stack" style={{gap:'10px', alignItems:'flex-start', marginTop:'4px'}}>
                                <p style={{flex:1, fontSize:'13px', opacity:0.8, whiteSpace:'pre-wrap', margin:0}}>{textoPieDefault || "(Sin texto configurado)"}</p>
                                <button className="secondary small" onClick={() => { setTextoPieDefaultEdit(textoPieDefault); setEditandoDefault(true); }}>✏️ Editar</button>
                            </div>
                        ) : (
                            <div style={{marginTop:'4px'}}>
                                <textarea 
                                    value={textoPieDefaultEdit} 
                                    onChange={e => setTextoPieDefaultEdit(e.target.value)} 
                                    rows={4} 
                                    style={{width:'100%', padding:'8px', borderRadius:'6px', border:'1px solid rgba(255,255,255,0.2)', background:'rgba(0,0,0,0.2)', color:'inherit', fontSize:'13px', resize:'vertical'}}
                                    placeholder="Ej: Este presupuesto tiene validez por XX días. Posteriormente, la oferente podrá modificarlo sin previo aviso..."
                                />
                                <div className="h-stack" style={{gap:'8px', marginTop:'6px'}}>
                                    <button className="primary small" onClick={guardarTextoPieDefault}>💾 Guardar por defecto</button>
                                    <button className="secondary small" onClick={() => setEditandoDefault(false)}>Cancelar</button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                <table className="table">
                    <thead><tr><th>Nº</th><th>Fecha</th><th>Cliente</th><th>Total</th><th>Estado Correo</th><th>Acción</th></tr></thead>
                    <tbody>
                        {presupuestos.length === 0 ? (
                            <tr><td colSpan={6} style={{textAlign:'center', padding:'2rem', opacity:0.5}}>No hay presupuestos aún. ¡Crea tu primero!</td></tr>
                        ) : presupuestos.map(p => (
                            <tr key={p.id}>
                                <td>{p.numero}</td>
                                <td>{new Date(p.fecha).toLocaleDateString()}</td>
                                <td>{p.cliente_nombre}</td>
                                <td>{p.total?.toLocaleString()}</td>
                                <td><span className={`badge ${p.email_enviado ? 'aprobado' : 'pendiente'}`}>{p.email_enviado ? '✉️ Enviado' : '📝 No Enviado'}</span></td>
                                <td>
                                    <button className="linkish" onClick={() => {
                                        setNumero(p.numero);
                                        setClienteNombre(p.cliente_nombre);
                                        setClienteEmail(p.cliente_email);
                                        setClienteTelefono(p.cliente_telefono);
                                        setValidezDias(p.validez_dias || 15);
                                        setTextoPie(p.texto_pie || textoPieDefault);
                                        setGrupos(p.grupos && p.grupos.length > 0 ? p.grupos.map((g: any) => ({
                                            id: Date.now() + Math.random(),
                                            nombre: g.nombre,
                                            es_suma: g.es_suma,
                                            conceptos: g.conceptos.map((c: any) => ({
                                                id: Date.now() + Math.random(),
                                                descripcion: c.descripcion,
                                                cantidad: c.cantidad,
                                                precio_unitario: c.precio_unitario,
                                                tasa_iva: c.tasa_iva ?? 10
                                            }))
                                        })) : [{ id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0, tasa_iva: 10 }] }]);
                                        setEditingId(p.id);
                                        setView("create");
                                    }}>Ver/Editar</button>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        );
    }

    // ---------- VISTA CREAR ----------
    return (
        <div className="card wide" style={{ backgroundColor: '#fff', color: '#000' }}>
            <div className="h-stack" style={{justifyContent: 'flex-end', marginBottom:'1rem', gap:'10px'}}>
                <button className="secondary" onClick={() => setView("list")}>← Cancelar</button>
                <button className="secondary" style={{borderColor:'#4b5563', color:'#4b5563'}} onClick={downloadPdf} disabled={isGeneratingPdf}>
                    {isGeneratingPdf ? "Generando..." : "📥 Descargar"}
                </button>
                <button className="primary" style={{backgroundColor:'#2563eb', color:'#fff'}} onClick={() => onSave(false)}>{editingId ? "💾 Guardar Cambios" : "💾 Solo Guardar"}</button>
                <button className="primary" style={{backgroundColor:'#059669', color:'#fff'}} onClick={() => onSave(true)}>📧 Guardar y Enviar</button>
            </div>

            {/* A4 Document Container */}
            <div ref={printRef} style={{ padding: '30px', minHeight: '297mm', maxWidth: '210mm', margin: '0 auto', border: '1px solid #ccc', backgroundColor: '#fff', fontFamily: 'Arial, sans-serif' }}>
                
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '3px solid #1a1a2e', paddingBottom: '15px', marginBottom: '25px' }}>
                    <div>
                        {logoUrl ? <img src={logoUrl} alt="Logo" style={{ height: '80px', objectFit: 'contain' }} /> : <div style={{height:'80px', width:'120px', border:'2px dashed #ccc', display:'flex', alignItems:'center', justifyContent:'center', color:'#999', fontSize:'11px'}}>LOGO</div>}
                    </div>
                    <div style={{ textAlign: 'right' }}>
                        <h1 style={{ margin: 0, fontSize: '26px', color: '#1a1a2e', letterSpacing: '2px' }}>PRESUPUESTO</h1>
                        <h2 style={{ margin: '5px 0', fontSize: '14px', color: '#555', fontWeight: 'normal' }}>{empresaNombre}</h2>
                        <div style={{marginTop:'8px', fontSize:'13px', color:'#333'}}>
                            Nº: <input type="number" style={{width:'80px', border:'none', borderBottom:'1px solid #999', outline:'none', background:'transparent', color:'#000', textAlign:'center', fontWeight:'bold'}} value={numero} onChange={e=>setNumero(e.target.value?Number(e.target.value):"")} placeholder="Auto" />
                        </div>
                        <div style={{fontSize:'13px', color:'#333', marginTop:'4px'}}>Fecha: {new Date().toLocaleDateString()}</div>
                    </div>
                </div>

                {/* Client Info */}
                <div style={{ marginBottom: '25px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', fontSize:'13px' }}>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Cliente</label>
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0 8px 0', lineHeight:'1.5', fontSize:'14px'}} value={clienteNombre} onChange={e=>setClienteNombre(e.target.value)} placeholder="Nombre del cliente" />
                    </div>
                    <div>
                        <label className="full">RUC <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0 8px 0', lineHeight:'1.5', fontSize:'14px'}} value={clienteRuc} onChange={e => setClienteRuc(e.target.value)} onBlur={e => onRucBlur(e.target.value)} placeholder="RUC del cliente" /></label>
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Email</label>
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0 8px 0', lineHeight:'1.5', fontSize:'14px'}} value={clienteEmail} onChange={e=>setClienteEmail(e.target.value)} placeholder="email@cliente.com" />
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Teléfono / Dirección</label>
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0 8px 0', lineHeight:'1.5', fontSize:'14px'}} value={clienteTelefono} onChange={e=>setClienteTelefono(e.target.value)} placeholder="Teléfono o dirección" />
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Validez</label>
                        <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                            <input type="number" style={{width:'50px', border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', padding:'4px 0 8px 0', lineHeight:'1.5', fontSize:'14px', textAlign:'center'}} value={validezDias} onChange={e=>setValidezDias(Number(e.target.value))} /> <span style={{color:'#555'}}>días</span>
                        </div>
                    </div>
                </div>

                {/* Cliente Status (NO PRINT) */}
                {clienteEncontrado && !clienteEncontrado._is_new_sifen ? (
                    <div className="alert success small h-stack no-print" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginBottom: '0.5rem'}}>
                        <span>✅ Cliente Registrado</span>
                        <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Actualizar Datos</button>
                    </div>
                ) : clienteEncontrado && clienteEncontrado._is_new_sifen ? (
                    <div className="alert info small h-stack no-print" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginBottom: '0.5rem'}}>
                        <span>ℹ️ RUC Válido - No registrado</span>
                        <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Agregar a Base de Datos</button>
                    </div>
                ) : clienteRuc && clienteRuc.length >= 5 ? (
                    <div className="alert warning small h-stack no-print" style={{justifyContent: 'space-between', padding: '0.5rem 1rem', marginBottom: '0.5rem'}}>
                        <span>⚠️ Cliente no encontrado</span>
                        <button type="button" className="secondary small" onClick={() => setShowClienteModal(true)}>Agregar Manualmente</button>
                    </div>
                ) : null}

                {/* Groups */}
                {grupos.map((g, gIdx) => (
                    <div key={g.id} style={{ marginBottom: '20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', backgroundColor: '#f4f6f8', padding: '8px 10px', border: '1px solid #ddd', borderRadius: '4px 4px 0 0' }}>
                            <select style={{marginRight:'10px', color:'#000', background:'transparent', border:'1px solid #ccc', borderRadius:'3px', padding:'2px 4px', fontWeight:'bold', fontSize:'12px'}} value={g.es_suma?"suma":"resta"} onChange={e=>{
                                const ng = [...grupos]; ng[gIdx].es_suma = e.target.value==="suma"; setGrupos(ng);
                            }}>
                                <option value="suma">(+)</option>
                                <option value="resta">(−) DESCUENTO</option>
                            </select>
                            
                            <input 
                                list="grupos-list"
                                style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none', fontWeight: 'bold', color: '#1a1a2e', fontSize: '14px' }} 
                                placeholder="Nombre del Grupo (ej. Honorarios Profesionales)"
                                value={g.nombre}
                                onChange={e => { const ng = [...grupos]; ng[gIdx].nombre = e.target.value; setGrupos(ng); }}
                            />
                            
                            {grupos.length > 1 && <button className="no-print" style={{background:'none', border:'none', color:'#dc2626', cursor:'pointer', fontSize:'16px', fontWeight:'bold'}} onClick={() => {
                                setGrupos(grupos.filter((_, i) => i !== gIdx));
                            }}>✕</button>}
                        </div>
                        
                        <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #ddd', borderTop:'none' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#f9fafb' }}>
                                    <th style={{ textAlign: 'left', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Descripción</th>
                                    <th style={{ width: '50px', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Cant.</th>
                                    <th style={{ width: '90px', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>P. Unitario</th>
                                    <th className="no-print" style={{ width: '60px', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>IVA</th>
                                    <th style={{ width: '80px', padding: '6px 8px', textAlign: 'right', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Exentas</th>
                                    <th style={{ width: '80px', padding: '6px 8px', textAlign: 'right', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>5%</th>
                                    <th style={{ width: '80px', padding: '6px 8px', textAlign: 'right', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>10%</th>
                                    <th style={{ width: '30px', borderBottom:'1px solid #ddd' }} className="no-print"></th>
                                </tr>
                            </thead>
                            <tbody>{/* */}{g.conceptos.map((c: any, cIdx: number) => {
                                const subt = c.cantidad * c.precio_unitario;
                                return (
                                    <tr key={c.id} style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd' }}>
                                            <input 
                                                list="conceptos-list"
                                                style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', fontSize:'13px', paddingBottom:'6px' }} 
                                                value={c.descripcion}
                                                placeholder="Descripción del concepto"
                                                onChange={e => {
                                                    const ng = [...grupos];
                                                    ng[gIdx].conceptos[cIdx].descripcion = e.target.value;
                                                    const match = sugConceptos.find(x => x.descripcion === e.target.value);
                                                    if(match && c.precio_unitario === 0) ng[gIdx].conceptos[cIdx].precio_unitario = match.precio;
                                                    setGrupos(ng);
                                                }}
                                            />
                                        </td>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd' }}>
                                            <input type="number" style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', textAlign:'center', fontSize:'13px', paddingBottom:'6px' }} value={c.cantidad} onChange={e => { const ng = [...grupos]; ng[gIdx].conceptos[cIdx].cantidad = Number(e.target.value); setGrupos(ng); }} />
                                        </td>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd' }}>
                                            <input type="number" style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', textAlign:'right', fontSize:'13px', paddingBottom:'6px' }} value={c.precio_unitario} onChange={e => { const ng = [...grupos]; ng[gIdx].conceptos[cIdx].precio_unitario = Number(e.target.value); setGrupos(ng); }} />
                                        </td>
                                        <td className="no-print" style={{ padding: '4px 8px', borderRight: '1px solid #ddd', textAlign:'center' }}>
                                            <select style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', fontSize:'12px', textAlign:'center' }} value={c.tasa_iva ?? 10} onChange={e => { const ng = [...grupos]; ng[gIdx].conceptos[cIdx].tasa_iva = Number(e.target.value); setGrupos(ng); }}>
                                                <option value={10}>10%</option>
                                                <option value={5}>5%</option>
                                                <option value={0}>Exento</option>
                                            </select>
                                        </td>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd', textAlign: 'right', color:'#000', fontWeight:'500', fontSize:'13px' }}>
                                            {c.tasa_iva === 0 ? subt.toLocaleString() : ""}
                                        </td>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd', textAlign: 'right', color:'#000', fontWeight:'500', fontSize:'13px' }}>
                                            {c.tasa_iva === 5 ? subt.toLocaleString() : ""}
                                        </td>
                                        <td style={{ padding: '4px 8px', textAlign: 'right', color:'#000', fontWeight:'500', fontSize:'13px' }}>
                                            {c.tasa_iva === 10 ? subt.toLocaleString() : ""}
                                        </td>
                                        <td style={{ textAlign: 'center' }} className="no-print">
                                            <button style={{background:'none', border:'none', color:'#dc2626', cursor:'pointer', fontSize:'13px'}} onClick={() => {
                                                const ng = [...grupos];
                                                ng[gIdx].conceptos = ng[gIdx].conceptos.filter((_:any, i:number) => i !== cIdx);
                                                setGrupos(ng);
                                            }}>✕</button>
                                        </td>
                                    </tr>
                                );
                            })}
                                <tr>
                                    <td colSpan={5} style={{ padding: '4px 8px' }}>
                                        <button className="no-print" style={{background:'none', border:'none', color:'#2563eb', cursor:'pointer', fontSize:'12px'}} onClick={() => {
                                            const ng = [...grupos];
                                            ng[gIdx].conceptos.push({ id: Date.now(), descripcion: "", cantidad: 1, precio_unitario: 0, tasa_iva: 10 });
                                            setGrupos(ng);
                                        }}>+ Añadir Concepto</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                ))}

                <button style={{marginBottom:'20px', background:'none', border:'1px dashed #999', padding:'6px 14px', cursor:'pointer', color:'#555', borderRadius:'4px', fontSize:'13px'}} onClick={() => {
                    setGrupos([...grupos, { id: Date.now(), nombre: "", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "", cantidad: 1, precio_unitario: 0, tasa_iva: 10 }] }]);
                }} className="no-print">+ Añadir Grupo</button>

                {/* Total */}
                <div style={{ marginTop: '20px' }}>
                    <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #1a1a2e', borderRadius:'4px' }}>
                        <tbody>
                            <tr style={{borderBottom:'1px solid #ccc'}}>
                                <td style={{ padding: '8px 14px', fontWeight: 'bold', fontSize:'12px', borderRight:'1px solid #ccc' }}>SUB-TOTALES</td>
                                <td style={{ padding: '8px 8px', textAlign: 'right', fontSize:'13px', borderRight:'1px solid #ccc', width:'80px' }}>{calcularTotalesIva().exentas.toLocaleString()}</td>
                                <td style={{ padding: '8px 8px', textAlign: 'right', fontSize:'13px', borderRight:'1px solid #ccc', width:'80px' }}>{calcularTotalesIva().iva5.toLocaleString()}</td>
                                <td style={{ padding: '8px 8px', textAlign: 'right', fontSize:'13px', width:'80px', borderRight:'1px solid #ccc' }}>{calcularTotalesIva().iva10.toLocaleString()}</td>
                                <td style={{ width: '30px' }} className="no-print"></td>
                            </tr>
                            <tr style={{borderBottom:'1px solid #ccc'}}>
                                <td colSpan={3} style={{ padding: '8px 14px', fontWeight: 'bold', fontSize:'12px', borderRight:'1px solid #ccc' }}>TOTAL</td>
                                <td style={{ padding: '8px 8px', textAlign: 'right', fontWeight: 'bold', fontSize:'13px', borderRight:'1px solid #ccc' }}>{calcularTotal().toLocaleString()}</td>
                                <td className="no-print"></td>
                            </tr>
                            <tr style={{borderBottom:'1px solid #ccc'}}>
                                <td colSpan={5} style={{ padding: '8px 14px', fontSize:'12px' }}>
                                    <div style={{display:'flex', justifyContent:'space-between', paddingRight: '40px'}}>
                                        <span>LIQUIDACIÓN DEL IVA (5%): {calcularTotalesIva().liq5.toLocaleString()}</span>
                                        <span>(10%): {calcularTotalesIva().liq10.toLocaleString()}</span>
                                        <span style={{fontWeight:'bold'}}>TOTAL IVA: {calcularTotalesIva().liqTotal.toLocaleString()}</span>
                                    </div>
                                </td>
                            </tr>
                            <tr style={{backgroundColor:'#1a1a2e'}}>
                                <td colSpan={3} style={{ padding: '10px 14px', fontWeight: 'bold', color:'#fff', fontSize:'12px', textTransform:'uppercase' }}>TOTAL A PAGAR: GUARANIES {numeroALetras(calcularTotal())}</td>
                                <td style={{ padding: '10px 8px', textAlign: 'right', fontWeight: 'bold', color:'#fff', fontSize:'15px', borderRight:'1px solid #ccc' }}>{calcularTotal().toLocaleString()}</td>
                                <td className="no-print"></td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <style>{`@media print { .no-print { display:none !important; } }`}</style>

                {/* Texto Pie - EDITABLE (solo visible en PDF con saltos de línea) */}
                <div style={{ marginTop: '40px', paddingTop: '15px', borderTop: '1px solid #ddd', whiteSpace: 'pre-wrap', wordWrap: 'break-word', fontSize: '12px', color: '#555', fontFamily: 'Arial, sans-serif', lineHeight: '1.5' }}>
                    {textoPie || ""}
                </div>
            </div>

            {/* Textarea para editar pie (FUERA del printRef, solo en frontend) */}
            <div style={{marginTop: '1rem', padding:'1rem', backgroundColor:'#f9f9f9', borderRadius:'6px'}}>
                <label style={{display:'block', fontWeight:'bold', marginBottom:'6px', fontSize:'13px'}}>Texto al Pie del Presupuesto</label>
                <textarea 
                    value={textoPie}
                    onChange={e => setTextoPie(e.target.value)}
                    rows={4}
                    style={{
                        width: '100%',
                        border: '1px solid #ccc',
                        borderRadius: '4px',
                        padding: '10px',
                        fontSize: '12px',
                        color: '#333',
                        background: '#fff',
                        resize: 'vertical',
                        fontFamily: 'Arial, sans-serif',
                        lineHeight: '1.5',
                        outline: 'none'
                    }}
                    placeholder="Ej: Este presupuesto tiene validez por XX días. Posteriormente, la oferente podrá modificarlo sin previo aviso..."
                />
                <p style={{margin:'4px 0 0', fontSize:'11px', color:'#666', fontStyle:'italic'}}>
                    ✏️ Este texto se guardará junto con el presupuesto y aparecerá en el PDF. Los saltos de línea se respetan.
                </p>
            </div>

            <datalist id="grupos-list">
                {sugGrupos.map(g => <option key={g} value={g} />)}
            </datalist>
            <datalist id="conceptos-list">
                {sugConceptos.map(c => <option key={c.descripcion} value={c.descripcion} />)}
            </datalist>

            {/* Modal para agregar/actualizar cliente */}
            {showClienteModal && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 1000
                }}>
                    <div style={{
                        backgroundColor: '#fff', color: '#000', padding: '2rem',
                        borderRadius: '8px', maxWidth: '500px', width: '90%',
                        boxShadow: '0 10px 40px rgba(0,0,0,0.3)'
                    }}>
                        <h3 style={{margin: '0 0 1.5rem 0', fontSize: '18px', fontWeight: 'bold'}}>
                            {clienteEncontrado?.id ? 'Actualizar Cliente' : 'Agregar Cliente'}
                        </h3>
                        
                        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem'}}>
                            <div>
                                <label style={{display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', textTransform: 'uppercase'}}>RUC</label>
                                <input 
                                    type="text" 
                                    value={clienteRuc} 
                                    onChange={e => setClienteRuc(e.target.value)}
                                    style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px'}}
                                    placeholder="Ej: 1234567-8"
                                />
                            </div>
                            <div>
                                <label style={{display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', textTransform: 'uppercase'}}>Nombre/Razón Social</label>
                                <input 
                                    type="text" 
                                    value={clienteNombre} 
                                    onChange={e => setClienteNombre(e.target.value)}
                                    style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px'}}
                                    placeholder="Nombre del cliente"
                                />
                            </div>
                            <div style={{gridColumn: '1 / -1'}}>
                                <label style={{display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', textTransform: 'uppercase'}}>Email</label>
                                <input 
                                    type="email" 
                                    value={clienteEmail} 
                                    onChange={e => setClienteEmail(e.target.value)}
                                    style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px'}}
                                    placeholder="email@cliente.com"
                                />
                            </div>
                            <div>
                                <label style={{display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', textTransform: 'uppercase'}}>Teléfono</label>
                                <input 
                                    type="text" 
                                    value={clienteTelefono} 
                                    onChange={e => setClienteTelefono(e.target.value)}
                                    style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px'}}
                                    placeholder="Teléfono"
                                />
                            </div>
                            <div>
                                <label style={{display: 'block', fontSize: '12px', fontWeight: 'bold', marginBottom: '4px', textTransform: 'uppercase'}}>Dirección</label>
                                <input 
                                    type="text" 
                                    value={clienteDir} 
                                    onChange={e => setClienteDir(e.target.value)}
                                    style={{width: '100%', padding: '8px', border: '1px solid #ccc', borderRadius: '4px', fontSize: '14px'}}
                                    placeholder="Dirección"
                                />
                            </div>
                        </div>

                        <div style={{display: 'flex', gap: '10px', justifyContent: 'flex-end'}}>
                            <button 
                                className="secondary" 
                                onClick={() => setShowClienteModal(false)}
                                style={{padding: '8px 16px', borderRadius: '4px'}}
                            >
                                Cancelar
                            </button>
                            <button 
                                className="primary"
                                onClick={async () => {
                                    try {
                                        if (!clienteNombre || !clienteRuc) {
                                            alert('Por favor ingrese nombre y RUC del cliente');
                                            return;
                                        }
                                        setLoading(true);
                                        await upsertCliente({
                                            ruc_con_dv: clienteRuc,
                                            razon_social: clienteNombre,
                                            email: clienteEmail,
                                            telefono: clienteTelefono,
                                            direccion: clienteDir,
                                        });
                                        alert('Cliente guardado exitosamente');
                                        setShowClienteModal(false);
                                        setClienteEncontrado({_is_new_sifen: false});
                                    } catch (e: any) {
                                        alert('Error al guardar cliente: ' + e.message);
                                    } finally {
                                        setLoading(false);
                                    }
                                }}
                                style={{padding: '8px 16px', borderRadius: '4px'}}
                                disabled={loading}
                            >
                                {loading ? 'Guardando...' : '💾 Guardar Cliente'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
