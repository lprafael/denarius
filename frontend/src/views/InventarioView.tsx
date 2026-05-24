import React, { useState } from "react";
import {
  createProducto,
  updateProducto,
  deleteProducto,
} from "../api";

interface InventarioViewProps {
  productos: any[];
  refresh: () => Promise<void>;
}

export function InventarioView({ productos, refresh }: InventarioViewProps) {
  const [showProductoModal, setShowProductoModal] = useState(false);
  const [editingProducto, setEditingProducto] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function onSaveProducto(e: React.FormEvent) {
    e.preventDefault();
    if (!editingProducto) return;
    setLoading(true);
    try {
      if (editingProducto.id) {
        await updateProducto(editingProducto.id, editingProducto);
      } else {
        await createProducto(editingProducto);
      }
      setShowProductoModal(false);
      setEditingProducto(null);
      await refresh();
    } catch (ex) {
      setErr(String(ex));
    } finally {
      setLoading(false);
    }
  }

  async function onDeleteProducto(id: number) {
    if (!window.confirm("¿Eliminar?")) return;
    try {
      await deleteProducto(id);
      await refresh();
    } catch (ex) {
      setErr(String(ex));
    }
  }

  return (
    <div className="card wide">
      {err && <div className="alert">{err}</div>}
      <div className="h-stack" style={{justifyContent:'space-between', marginBottom:'1.5rem'}}>
        <h2>Gestión de Stock</h2>
        <button className="primary" onClick={() => { setEditingProducto({ sku: "", descripcion: "", precio_venta: 0, precio_costo: 0, stock_actual: 0 }); setShowProductoModal(true); }}>+ Nuevo Producto</button>
      </div>
      <table className="table">
        <thead><tr><th>SKU</th><th>Descripción</th><th>Stock</th><th>Precio</th><th>Acciones</th></tr></thead>
        <tbody>
          {productos.map(p => (
            <tr key={p.id}>
              <td className="mono">{p.sku}</td>
              <td>{p.descripcion}</td>
              <td className={p.stock_actual < 5 ? 'error-text' : 'success-text'}>{p.stock_actual}</td>
              <td>{p.precio_venta.toLocaleString()}</td>
              <td>
                <button className="linkish" onClick={() => { setEditingProducto(p); setShowProductoModal(true); }}>✏️</button>
                {" | "}
                <button className="linkish danger" onClick={() => onDeleteProducto(p.id)}>🗑️</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showProductoModal && editingProducto && (
        <div className="modal-overlay" onClick={()=>setShowProductoModal(false)}>
          <div className="modal-content" onClick={e=>e.stopPropagation()} style={{background:'var(--panel)', padding:'2rem', borderRadius:'12px', width:'400px'}}>
            <h2>{editingProducto.id ? "Editar" : "Nuevo"} Producto</h2>
            <form onSubmit={onSaveProducto} className="form">
              <label className="full">SKU <input value={editingProducto.sku} onChange={e=>setEditingProducto({...editingProducto, sku:e.target.value})} /></label>
              <label className="full">Descripción <input value={editingProducto.descripcion} onChange={e=>setEditingProducto({...editingProducto, descripcion:e.target.value})} /></label>
              <label>Venta Gs. <input type="number" value={editingProducto.precio_venta} onChange={e=>setEditingProducto({...editingProducto, precio_venta:Number(e.target.value)})} /></label>
              <label>Stock <input type="number" value={editingProducto.stock_actual} onChange={e=>setEditingProducto({...editingProducto, stock_actual:Number(e.target.value)})} /></label>
              <button type="submit" className="primary full" style={{marginTop:'1rem'}} disabled={loading}>Guardar Cambios</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
