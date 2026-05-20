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
    updatePresupuestoConfig
} from "./api";

export function PresupuestosView({ empresaNombre }: { empresaNombre: string }) {
    const [view, setView] = useState<"list" | "create">("list");
    const [presupuestos, setPresupuestos] = useState<any[]>([]);
    const [logoUrl, setLogoUrl] = useState<string>("");
    
    // Auto-complete data
    const [sugGrupos, setSugGrupos] = useState<string[]>([]);
    const [sugConceptos, setSugConceptos] = useState<any[]>([]);

    // Form state
    const [clienteNombre, setClienteNombre] = useState("");
    const [clienteEmail, setClienteEmail] = useState("");
    const [clienteTelefono, setClienteTelefono] = useState("");
    const [numero, setNumero] = useState<number | "">("");
    const [validezDias, setValidezDias] = useState<number>(15);
    
    // Texto pie editable - se carga desde la config de la empresa
    const [textoPie, setTextoPie] = useState("");
    const [textoPieDefault, setTextoPieDefault] = useState("");
    const [editandoDefault, setEditandoDefault] = useState(false);
    const [textoPieDefaultEdit, setTextoPieDefaultEdit] = useState("");
    
    const [grupos, setGrupos] = useState<any[]>([
        { id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0 }] }
    ]);

    const printRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (view === "list") loadData();
        loadConfig();
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

    function calcularTotal() {
        let total = 0;
        for (const g of grupos) {
            let subt = 0;
            for (const c of g.conceptos) {
                subt += (c.cantidad * c.precio_unitario);
            }
            if (g.es_suma) total += subt;
            else total -= subt;
        }
        return total;
    }

    async function generatePdfBase64(): Promise<string> {
        if (!printRef.current) return "";
        const canvas = await html2canvas(printRef.current, { scale: 2 });
        const imgData = canvas.toDataURL("image/png");
        const pdf = new jsPDF("p", "mm", "a4");
        const pdfWidth = pdf.internal.pageSize.getWidth();
        const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
        pdf.addImage(imgData, "PNG", 0, 0, pdfWidth, pdfHeight);
        
        const pdfDataUri = pdf.output("datauristring");
        return pdfDataUri.split(",")[1];
    }

    async function onSave(enviar: boolean) {
        try {
            if (!clienteNombre) return alert("Ingrese el nombre del cliente");
            
            const payload = {
                numero: numero || undefined,
                cliente_nombre: clienteNombre,
                cliente_email: clienteEmail,
                cliente_telefono: clienteTelefono,
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
                        orden: j
                    }))
                }))
            };

            const saved = await createPresupuesto(payload);
            
            if (enviar && clienteEmail) {
                const base64 = await generatePdfBase64();
                await enviarPresupuesto(saved.id, {
                    pdf_base64: base64,
                    destinatario: clienteEmail,
                    asunto: `Presupuesto Nº ${saved.numero} - ${empresaNombre}`,
                    mensaje: `Estimado/a ${clienteNombre},\n\nAdjuntamos el presupuesto solicitado.\n\nSaludos,\n${empresaNombre}`
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
                        setTextoPie(textoPieDefault);
                        setClienteNombre("");
                        setClienteEmail("");
                        setClienteTelefono("");
                        setNumero("");
                        setGrupos([{ id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0 }] }]);
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
                                                precio_unitario: c.precio_unitario
                                            }))
                                        })) : [{ id: Date.now(), nombre: "Honorarios", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "Servicio", cantidad: 1, precio_unitario: 0 }] }]);
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
                <button className="primary" style={{backgroundColor:'#2563eb', color:'#fff'}} onClick={() => onSave(false)}>💾 Solo Guardar</button>
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
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0', fontSize:'14px'}} value={clienteNombre} onChange={e=>setClienteNombre(e.target.value)} placeholder="Nombre del cliente" />
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Email</label>
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0', fontSize:'14px'}} value={clienteEmail} onChange={e=>setClienteEmail(e.target.value)} placeholder="email@cliente.com" />
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Teléfono / Dirección</label>
                        <input style={{border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', width:'100%', padding:'4px 0', fontSize:'14px'}} value={clienteTelefono} onChange={e=>setClienteTelefono(e.target.value)} placeholder="Teléfono o dirección" />
                    </div>
                    <div>
                        <label style={{display:'block', fontWeight:'bold', marginBottom:'4px', color:'#555', fontSize:'11px', textTransform:'uppercase'}}>Validez</label>
                        <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                            <input type="number" style={{width:'50px', border:'none', borderBottom:'1px solid #ccc', outline:'none', background:'transparent', color:'#000', padding:'4px 0', fontSize:'14px', textAlign:'center'}} value={validezDias} onChange={e=>setValidezDias(Number(e.target.value))} /> <span style={{color:'#555'}}>días</span>
                        </div>
                    </div>
                </div>

                {/* Groups */}
                {grupos.map((g, gIdx) => (
                    <div key={g.id} style={{ marginBottom: '20px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', backgroundColor: '#f4f6f8', padding: '8px 10px', border: '1px solid #ddd', borderRadius: '4px 4px 0 0' }}>
                            <select style={{marginRight:'10px', color:'#000', background:'transparent', border:'1px solid #ccc', borderRadius:'3px', padding:'2px 4px', fontWeight:'bold', fontSize:'12px'}} value={g.es_suma?"suma":"resta"} onChange={e=>{
                                const ng = [...grupos]; ng[gIdx].es_suma = e.target.value==="suma"; setGrupos(ng);
                            }}>
                                <option value="suma">(+) SUMA</option>
                                <option value="resta">(−) DESCUENTO</option>
                            </select>
                            
                            <input 
                                list="grupos-list"
                                style={{ flex: 1, border: 'none', background: 'transparent', outline: 'none', fontWeight: 'bold', color: '#1a1a2e', fontSize: '14px' }} 
                                placeholder="Nombre del Grupo (ej. Honorarios Profesionales)"
                                value={g.nombre}
                                onChange={e => { const ng = [...grupos]; ng[gIdx].nombre = e.target.value; setGrupos(ng); }}
                            />
                            
                            {grupos.length > 1 && <button style={{background:'none', border:'none', color:'#dc2626', cursor:'pointer', fontSize:'16px', fontWeight:'bold'}} onClick={() => {
                                setGrupos(grupos.filter((_, i) => i !== gIdx));
                            }}>✕</button>}
                        </div>
                        
                        <table style={{ width: '100%', borderCollapse: 'collapse', border: '1px solid #ddd', borderTop:'none' }}>
                            <thead>
                                <tr style={{ backgroundColor: '#f9fafb' }}>
                                    <th style={{ textAlign: 'left', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Descripción</th>
                                    <th style={{ width: '60px', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Cant.</th>
                                    <th style={{ width: '110px', padding: '6px 8px', borderRight: '1px solid #ddd', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>P. Unitario</th>
                                    <th style={{ width: '120px', padding: '6px 8px', textAlign: 'right', borderBottom:'1px solid #ddd', color:'#555', fontSize:'11px', textTransform:'uppercase' }}>Subtotal</th>
                                    <th style={{ width: '30px', borderBottom:'1px solid #ddd' }}></th>
                                </tr>
                            </thead>
                            <tbody>
                                {g.conceptos.map((c: any, cIdx: number) => (
                                    <tr key={c.id} style={{ borderBottom: '1px solid #eee' }}>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd' }}>
                                            <input 
                                                list="conceptos-list"
                                                style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', fontSize:'13px' }} 
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
                                            <input type="number" style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', textAlign:'center', fontSize:'13px' }} value={c.cantidad} onChange={e => { const ng = [...grupos]; ng[gIdx].conceptos[cIdx].cantidad = Number(e.target.value); setGrupos(ng); }} />
                                        </td>
                                        <td style={{ padding: '4px 8px', borderRight: '1px solid #ddd' }}>
                                            <input type="number" style={{ width: '100%', border: 'none', background: 'transparent', outline: 'none', color:'#000', textAlign:'right', fontSize:'13px' }} value={c.precio_unitario} onChange={e => { const ng = [...grupos]; ng[gIdx].conceptos[cIdx].precio_unitario = Number(e.target.value); setGrupos(ng); }} />
                                        </td>
                                        <td style={{ padding: '4px 8px', textAlign: 'right', color:'#000', fontWeight:'500', fontSize:'13px' }}>
                                            {(c.cantidad * c.precio_unitario).toLocaleString()}
                                        </td>
                                        <td style={{ textAlign: 'center' }}>
                                            <button style={{background:'none', border:'none', color:'#dc2626', cursor:'pointer', fontSize:'13px'}} onClick={() => {
                                                const ng = [...grupos];
                                                ng[gIdx].conceptos = ng[gIdx].conceptos.filter((_:any, i:number) => i !== cIdx);
                                                setGrupos(ng);
                                            }}>✕</button>
                                        </td>
                                    </tr>
                                ))}
                                <tr>
                                    <td colSpan={5} style={{ padding: '4px 8px' }}>
                                        <button style={{background:'none', border:'none', color:'#2563eb', cursor:'pointer', fontSize:'12px'}} onClick={() => {
                                            const ng = [...grupos];
                                            ng[gIdx].conceptos.push({ id: Date.now(), descripcion: "", cantidad: 1, precio_unitario: 0 });
                                            setGrupos(ng);
                                        }}>+ Añadir Concepto</button>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                ))}

                <button style={{marginBottom:'20px', background:'none', border:'1px dashed #999', padding:'6px 14px', cursor:'pointer', color:'#555', borderRadius:'4px', fontSize:'13px'}} onClick={() => {
                    setGrupos([...grupos, { id: Date.now(), nombre: "", es_suma: true, conceptos: [{ id: Date.now()+1, descripcion: "", cantidad: 1, precio_unitario: 0 }] }]);
                }}>+ Añadir Grupo</button>

                {/* Total */}
                <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '20px' }}>
                    <table style={{ width: '300px', borderCollapse: 'collapse', border: '2px solid #1a1a2e', borderRadius:'4px' }}>
                        <tbody>
                            <tr style={{backgroundColor:'#1a1a2e'}}>
                                <td style={{ padding: '10px 14px', fontWeight: 'bold', color:'#fff', fontSize:'14px' }}>TOTAL A PAGAR</td>
                                <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 'bold', color:'#fff', fontSize:'16px' }}>{calcularTotal().toLocaleString()}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                {/* Texto Pie - EDITABLE */}
                <div style={{ marginTop: '40px', paddingTop: '15px', borderTop: '1px solid #ddd' }}>
                    <textarea 
                        value={textoPie}
                        onChange={e => setTextoPie(e.target.value)}
                        rows={4}
                        style={{
                            width: '100%',
                            border: '1px dashed #ccc',
                            borderRadius: '4px',
                            padding: '10px',
                            fontSize: '12px',
                            color: '#555',
                            background: 'rgba(0,0,0,0.02)',
                            resize: 'vertical',
                            fontFamily: 'Arial, sans-serif',
                            lineHeight: '1.5',
                            outline: 'none'
                        }}
                        placeholder="Ej: Este presupuesto tiene validez por XX días. Posteriormente, la oferente podrá modificarlo sin previo aviso..."
                    />
                    <p style={{margin:'4px 0 0', fontSize:'10px', color:'#999', fontStyle:'italic'}}>
                        ✏️ Este texto se guardará junto con el presupuesto y aparecerá en el PDF.
                    </p>
                </div>
            </div>

            <datalist id="grupos-list">
                {sugGrupos.map(g => <option key={g} value={g} />)}
            </datalist>
            <datalist id="conceptos-list">
                {sugConceptos.map(c => <option key={c.descripcion} value={c.descripcion} />)}
            </datalist>
        </div>
    );
}
