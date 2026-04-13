const API = "/api";

let accessToken = "";

export function setAccessToken(token: string) {
  accessToken = token;
  if (token) localStorage.setItem("denarius_token", token);
  else localStorage.removeItem("denarius_token");
}

export function restoreAccessToken() {
  const t = localStorage.getItem("denarius_token") || "";
  accessToken = t;
  return t;
}

function authHeaders(): Record<string, string> {
  return accessToken ? { Authorization: `Bearer ${accessToken}` } : {};
}

export type LineaIn = {
  producto_id?: number;
  d_cod_int: string;
  d_des_pro_ser: string;
  d_cant_pro_ser: number;
  d_p_uni_pro_ser: number;
  d_tasa_iva: number;
};

export type FacturaCreate = {
  receptor_ruc: string;
  receptor_dv: string;
  receptor_nombre: string;
  receptor_dir?: string;
  receptor_tel?: string;
  receptor_email?: string;
  lineas: LineaIn[];
};

export type FacturaOut = {
  id: number;
  empresa_id: number;
  cdc: string;
  numero_documento: number;
  d_fe_emi_de: string;
  receptor_nombre: string;
  d_tot_gral_ope: number;
  d_tot_iva: number;
  estado_envio: string;
  created_at: string;
};


export type EmisorOut = {
  id: number;
  empresa_id: number;
  ruc_con_dv: string;
  razon_social: string;
  ultimo_num_doc: number;
  id_csc: string;
  csc_secreto: string;
};

export type EmpresaOut = {
  id: number;
  nombre: string;
  estado: string;
  created_at: string;
};

export type LoginOut = {
  access_token: string;
  token_type: string;
  empresa_id: number;
  empresa_nombre: string;
  usuario_email: string;
  rol: string;
};

export async function getHealth(): Promise<{ ok: boolean; nombre: string }> {
  const r = await fetch(`${API}/health`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getEmisor(): Promise<EmisorOut> {
  const r = await fetch(`${API}/emisor`, { headers: { ...authHeaders() } });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateEmisor(body: any): Promise<EmisorOut> {
  const r = await fetch(`${API}/emisor`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}


export async function listFacturas(empresaId?: number): Promise<FacturaOut[]> {
  const params = new URLSearchParams();
  if (empresaId) params.append("empresa_id", empresaId.toString());
  const queryString = params.toString();
  const url = queryString ? `${API}/facturas?${queryString}` : `${API}/facturas`;
  const r = await fetch(url, { headers: { ...authHeaders() } });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function createFactura(body: FacturaCreate): Promise<FacturaOut> {
  const r = await fetch(`${API}/facturas`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const t = await r.text();
    throw new Error(t);
  }
  return r.json();
}

export async function getXml(facturaId: number): Promise<string> {
  const r = await fetch(`${API}/facturas/${facturaId}/xml`, { headers: { ...authHeaders() } });
  if (!r.ok) throw new Error(await r.text());
  return r.text();
}

export async function getKudeHtml(facturaId: number): Promise<string> {
  const r = await fetch(`${API}/facturas/${facturaId}/kude`, { headers: { ...authHeaders() } });
  if (!r.ok) throw new Error(await r.text());
  return r.text();
}

export async function consultarRuc(ruc: string): Promise<any> {
  const r = await fetch(`${API}/facturas/consultar-ruc/${ruc}`, {
    headers: { ...authHeaders() },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getClienteByRuc(ruc: string): Promise<any> {
  const r = await fetch(`${API}/clientes/${ruc}`, {
    headers: { ...authHeaders() },
  });
  if (r.status === 404) return null;
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function upsertCliente(body: any): Promise<any> {
  const r = await fetch(`${API}/clientes`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getDepartamentos(): Promise<any[]> {
  const r = await fetch(`${API}/clientes/geo/departamentos`, {
    headers: { ...authHeaders() },
  });
  if (!r.ok) return [];
  return r.json();
}

export async function getDistritos(dptoId: number): Promise<any[]> {
  const r = await fetch(`${API}/clientes/geo/distritos/${dptoId}`, {
    headers: { ...authHeaders() },
  });
  if (!r.ok) return [];
  return r.json();
}

export async function getBarrios(dptoId: number, distId: number): Promise<any[]> {
  const r = await fetch(`${API}/clientes/geo/barrios/${dptoId}/${distId}`, {
    headers: { ...authHeaders() },
  });
  if (!r.ok) return [];
  return r.json();
}

export async function registrarEmpresa(body: {
  nombre: string;
  email_admin: string;
  password_admin?: string;
  ruc_con_dv: string;
  razon_social: string;
  google_token?: string;
}): Promise<EmpresaOut> {

  const r = await fetch(`${API}/auth/registro-empresa`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function login(email: string, password: string, device_id?: string): Promise<LoginOut> {
  const r = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, device_id }),
  });

  if (!r.ok) throw new Error(await r.text());
  const out: LoginOut = await r.json();
  setAccessToken(out.access_token);
  return out;
}

export async function googleLogin(credential: string, device_id?: string): Promise<LoginOut> {
    const r = await fetch(`${API}/auth/google-login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ credential, device_id }),
    });
    if (!r.ok) {
        const t = await r.text();
        throw new Error(t);
    }
    const out: LoginOut = await r.json();
    setAccessToken(out.access_token);
    return out;
}


export async function listEmpresasGlobal(): Promise<any[]> {
  const r = await fetch(`${API}/empresas`, { headers: { ...authHeaders() } });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getAdminDashboard(): Promise<any> {
    const r = await fetch(`${API}/empresas/dashboard`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}


export async function toggleEmpresa(id: number): Promise<any> {
  const r = await fetch(`${API}/empresas/${id}/toggle`, {
    method: "PUT",
    headers: { ...authHeaders() },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function deleteEmpresa(id: number): Promise<any> {
  const r = await fetch(`${API}/empresas/${id}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function updateEmpresa(id: number, body: any): Promise<any> {
  const r = await fetch(`${API}/empresas/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function createSuperAdmin(nombre: string, email: string, pass: string): Promise<any> {
  const r = await fetch(`${API}/empresas/admins?nombre=${encodeURIComponent(nombre)}&email=${encodeURIComponent(email)}&password=${encodeURIComponent(pass)}`, {
    method: "POST",
    headers: { ...authHeaders() },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function downloadDoc(filename: string): Promise<Blob> {
  const r = await fetch(`${API}/docs/download/${filename}`, {
    headers: { ...authHeaders() },
  });
  if (!r.ok) throw new Error(await r.text());
  return r.blob();
}

// Equipos
export async function listEquipos(): Promise<any[]> {
    const r = await fetch(`${API}/equipos`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function updateEquipo(id: number, body: { autorizado?: boolean; descripcion?: string }): Promise<any> {
    const r = await fetch(`${API}/equipos/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function deleteEquipo(id: number): Promise<any> {
    const r = await fetch(`${API}/equipos/${id}`, {
        method: "DELETE",
        headers: { ...authHeaders() },
    });
    if (!r.ok) throw new Error(await r.text());
    return null;
}

// Productos
export async function listProductos(): Promise<any[]> {
    const r = await fetch(`${API}/productos`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function createProducto(body: any): Promise<any> {
    const r = await fetch(`${API}/productos`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function updateProducto(id: number, body: any): Promise<any> {
    const r = await fetch(`${API}/productos/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function deleteProducto(id: number): Promise<any> {
    const r = await fetch(`${API}/productos/${id}`, {
        method: "DELETE",
        headers: { ...authHeaders() },
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

// Compras
export async function listCompras(): Promise<any[]> {
    const r = await fetch(`${API}/compras`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function syncCompras(): Promise<any> {
    const r = await fetch(`${API}/compras/sync`, {
        method: "POST",
        headers: { ...authHeaders() },
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

// Analítica
export async function getProyeccionIva(): Promise<any> {
    const r = await fetch(`${API}/analitica/proyeccion-iva`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function getStatsVentas(): Promise<any[]> {
    const r = await fetch(`${API}/analitica/ventas-mensuales`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function getTopProductos(): Promise<any[]> {
    const r = await fetch(`${API}/analitica/productos-top`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function listUsuarios(): Promise<any[]> {
    const r = await fetch(`${API}/usuarios`, { headers: { ...authHeaders() } });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function createUsuario(body: any): Promise<any> {
    const r = await fetch(`${API}/usuarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}

export async function deleteUsuario(id: number): Promise<any> {
    const r = await fetch(`${API}/usuarios/${id}`, {
        method: "DELETE",
        headers: { ...authHeaders() },
    });
    if (!r.ok) throw new Error(await r.text());
    return null;
}

export async function updateUsuario(id: number, body: any): Promise<any> {
    const r = await fetch(`${API}/usuarios/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body: JSON.stringify(body),
    });
    if (!r.ok) throw new Error(await r.text());
    return r.json();
}
