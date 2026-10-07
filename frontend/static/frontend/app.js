'use strict';
// Todo el contenido dinamico se inserta con textContent (anti-XSS); nunca innerHTML con datos.

const ESTADOS = ['disponible', 'reservado', 'vendido'];
const TIPOS = ['sedan', 'suv', 'pickup', 'hatchback', 'coupe', 'otro'];
const CARGOS = ['vendedor', 'gerente', 'tecnico'];
const PAGOS = ['contado', 'credito', 'leasing'];

// fk: [endpoint, campo a mostrar]
const ENTIDADES = {
  vehiculos: { titulo: 'Vehículos', cols: ['vin', 'modelo_nombre', 'anio', 'color', 'kilometraje', 'precio', 'estado'],
    campos: [['vin', 'VIN', 'text'], ['modelo', 'Modelo', 'fk', ['modelos', 'nombre']], ['anio', 'Año', 'number'],
      ['color', 'Color', 'text'], ['kilometraje', 'Kilometraje', 'number'], ['precio', 'Precio', 'number'],
      ['estado', 'Estado', 'select', ESTADOS], ['fecha_ingreso', 'Fecha ingreso', 'date']] },
  marcas: { titulo: 'Marcas', cols: ['nombre', 'pais_origen'],
    campos: [['nombre', 'Nombre', 'text'], ['pais_origen', 'País de origen', 'text']] },
  modelos: { titulo: 'Modelos', cols: ['nombre', 'tipo', 'marca_nombre'],
    campos: [['nombre', 'Nombre', 'text'], ['tipo', 'Tipo', 'select', TIPOS], ['marca', 'Marca', 'fk', ['marcas', 'nombre']]] },
  clientes: { titulo: 'Clientes', cols: ['documento', 'nombres', 'apellidos', 'email', 'telefono'],
    campos: [['documento', 'Documento', 'text'], ['nombres', 'Nombres', 'text'], ['apellidos', 'Apellidos', 'text'],
      ['email', 'Email', 'email'], ['telefono', 'Teléfono', 'text'], ['direccion', 'Dirección', 'text']] },
  empleados: { titulo: 'Empleados', cols: ['username', 'cargo', 'comision_pct'],
    campos: [['user', 'ID de usuario', 'number'], ['cargo', 'Cargo', 'select', CARGOS], ['comision_pct', 'Comisión %', 'number']] },
  ventas: { titulo: 'Ventas', cols: ['id', 'vehiculo', 'cliente', 'empleado', 'fecha', 'precio_final', 'metodo_pago'],
    campos: [['vehiculo', 'Vehículo', 'fk', ['vehiculos', 'vin']], ['cliente', 'Cliente', 'fk', ['clientes', 'documento']],
      ['empleado', 'Empleado', 'fk', ['empleados', 'username']], ['fecha', 'Fecha', 'date'],
      ['precio_final', 'Precio final', 'number'], ['metodo_pago', 'Método de pago', 'select', PAGOS]] },
  mantenimientos: { titulo: 'Mantenimientos', cols: ['id', 'vehiculo', 'tecnico', 'fecha', 'descripcion', 'costo'],
    campos: [['vehiculo', 'Vehículo', 'fk', ['vehiculos', 'vin']], ['tecnico', 'Técnico', 'fk', ['empleados', 'username']],
      ['fecha', 'Fecha', 'date'], ['descripcion', 'Descripción', 'text'], ['costo', 'Costo', 'number']] },
  auditoria: { titulo: 'Auditoría', soloLectura: true,
    cols: ['timestamp', 'usuario', 'ip', 'accion', 'tabla', 'registro_id', 'endpoint', 'status_code'], campos: [] },
};

const $ = (id) => document.getElementById(id);
let actual = 'vehiculos', pagina = 1, editando = null;
const modal = new bootstrap.Modal($('modal'));

function el(tag, text, cls) {
  const n = document.createElement(tag);
  if (text !== undefined && text !== null) n.textContent = String(text);
  if (cls) n.className = cls;
  return n;
}

async function api(path, opts = {}, reintento = true) {
  const r = await fetch('/api/v1/' + path, {
    ...opts,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + sessionStorage.getItem('access'), ...(opts.headers || {}) },
  });
  if (r.status === 401 && reintento && (await refrescar())) return api(path, opts, false);
  if (r.status === 401) { salir(); throw new Error('Sesión expirada'); }
  return r;
}

async function refrescar() {
  const refresh = sessionStorage.getItem('refresh');
  if (!refresh) return false;
  const r = await fetch('/api/v1/auth/refresh/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh }) });
  if (!r.ok) return false;
  const t = await r.json();
  sessionStorage.setItem('access', t.access);
  if (t.refresh) sessionStorage.setItem('refresh', t.refresh);
  return true;
}

async function salir() {
  const refresh = sessionStorage.getItem('refresh');
  // Invalida el refresh token en el servidor (blacklist) antes de limpiar la sesion.
  if (refresh) { try { await fetch('/api/v1/auth/logout/', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ refresh }) }); } catch (e) { /* sin red: igual se cierra localmente */ } }
  sessionStorage.clear(); location.href = '/login/';
}

function aviso(msg) { const a = $('aviso'); a.textContent = msg || ''; a.classList.toggle('d-none', !msg); }

function pintarTabs() {
  const ul = $('tabs'); ul.replaceChildren();
  for (const [k, e] of Object.entries(ENTIDADES)) {
    const li = el('li', null, 'nav-item'), b = el('button', e.titulo, 'nav-link' + (k === actual ? ' active' : ''));
    b.addEventListener('click', () => { actual = k; pagina = 1; $('buscar').value = ''; pintarTabs(); cargar(); });
    li.appendChild(b); ul.appendChild(li);
  }
  $('btn-nuevo').classList.toggle('d-none', !!ENTIDADES[actual].soloLectura);
}

async function cargar() {
  aviso('');
  const e = ENTIDADES[actual];
  const q = new URLSearchParams({ page: pagina });
  if ($('buscar').value.trim()) q.set('search', $('buscar').value.trim());
  const r = await api(`${actual}/?${q}`);
  if (r.status === 403) { aviso('No tiene permiso para ver esta sección.'); $('tbody').replaceChildren(); return; }
  if (!r.ok) { aviso('Error al cargar datos.'); return; }
  const data = await r.json();
  const tr = el('tr'); e.cols.forEach((c) => tr.appendChild(el('th', c))); if (!e.soloLectura) tr.appendChild(el('th', ''));
  $('thead').replaceChildren(tr);
  const filas = data.results.map((row) => {
    const t = el('tr'); e.cols.forEach((c) => t.appendChild(el('td', row[c])));
    if (!e.soloLectura) {
      const td = el('td', null, 'text-end text-nowrap');
      const be = el('button', 'Editar', 'btn btn-sm btn-outline-primary me-1'), bd = el('button', 'Borrar', 'btn btn-sm btn-outline-danger');
      be.addEventListener('click', () => abrirForm(row)); bd.addEventListener('click', () => borrar(row));
      td.append(be, bd); t.appendChild(td);
    }
    return t;
  });
  $('tbody').replaceChildren(...filas);
  $('pagina').textContent = `Página ${pagina} · ${data.count} registros`;
  $('prev').disabled = !data.previous; $('next').disabled = !data.next;
}

async function abrirForm(row) {
  editando = row || null;
  const e = ENTIDADES[actual];
  $('modal-titulo').textContent = (row ? 'Editar ' : 'Nuevo ') + e.titulo.toLowerCase();
  $('form-error').textContent = '';
  const cont = $('campos'); cont.replaceChildren();
  for (const [name, label, tipo, extra] of e.campos) {
    const g = el('div', null, 'mb-3'), l = el('label', label, 'form-label');
    let inp;
    if (tipo === 'select' || tipo === 'fk') {
      inp = el('select', null, 'form-select');
      let opts = extra;
      if (tipo === 'fk') {
        const r = await api(`${extra[0]}/?page_size=200`); const d = await r.json();
        opts = (d.results || []).map((o) => [o.id, o[extra[1]] ?? o.id]);
      }
      for (const o of opts) { const [v, t] = Array.isArray(o) ? o : [o, o]; const op = el('option', t); op.value = v; inp.appendChild(op); }
    } else {
      inp = el('input', null, 'form-control'); inp.type = tipo; if (tipo === 'number') inp.step = 'any';
    }
    inp.name = name; if (row && row[name] !== undefined) inp.value = row[name];
    g.append(l, inp); cont.appendChild(g);
  }
  modal.show();
}

$('form').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  const body = {};
  new FormData($('form')).forEach((v, k) => { if (v !== '') body[k] = v; });
  const r = await api(editando ? `${actual}/${editando.id}/` : `${actual}/`, { method: editando ? 'PUT' : 'POST', body: JSON.stringify(body) });
  if (r.ok) { modal.hide(); cargar(); return; }
  if (r.status === 403) { $('form-error').textContent = 'No tiene permiso para esta operación.'; return; }
  const err = await r.json().catch(() => ({}));
  $('form-error').textContent = Object.entries(err).map(([k, v]) => `${k}: ${[].concat(v).join(' ')}`).join(' | ') || 'Error al guardar.';
});

async function borrar(row) {
  if (!confirm('¿Eliminar este registro?')) return;
  const r = await api(`${actual}/${row.id}/`, { method: 'DELETE' });
  if (r.status === 403) aviso('No tiene permiso para eliminar.');
  else if (r.status === 409 || r.status === 500) aviso('No se puede eliminar: tiene registros relacionados.');
  cargar();
}

$('btn-nuevo').addEventListener('click', () => abrirForm(null));
$('btn-salir').addEventListener('click', salir);
$('prev').addEventListener('click', () => { pagina--; cargar(); });
$('next').addEventListener('click', () => { pagina++; cargar(); });
let t; $('buscar').addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { pagina = 1; cargar(); }, 300); });

if (!sessionStorage.getItem('access')) { location.href = '/login/'; } else { pintarTabs(); cargar(); }
