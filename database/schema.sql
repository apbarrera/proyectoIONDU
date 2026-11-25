--
-- PostgreSQL database dump
--
-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

-- Started on 2026-10-18 21:57:17

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 248 (class 1259 OID 16730)
-- Name: accion_ia; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.accion_ia (
    id_accion_ia integer NOT NULL,
    id_empresa integer NOT NULL,
    id_usuario integer,
    tipo_accion character varying(50) NOT NULL,
    instruccion_recibida text NOT NULL,
    payload_json jsonb,
    estado character varying(20) DEFAULT 'PENDIENTE'::character varying NOT NULL,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- TOC entry 247 (class 1259 OID 16729)
-- Name: accion_ia_id_accion_ia_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.accion_ia_id_accion_ia_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5205 (class 0 OID 0)
-- Dependencies: 247
-- Name: accion_ia_id_accion_ia_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.accion_ia_id_accion_ia_seq OWNED BY public.accion_ia.id_accion_ia;


--
-- TOC entry 240 (class 1259 OID 16620)
-- Name: categoria_gasto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categoria_gasto (
    id_categoria_gasto integer NOT NULL,
    id_empresa integer NOT NULL,
    nombre character varying(100) NOT NULL,
    origen character varying(50) DEFAULT 'PREDEFINIDA'::character varying NOT NULL,
    descripcion character varying(255)
);


--
-- TOC entry 239 (class 1259 OID 16619)
-- Name: categoria_gasto_id_categoria_gasto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categoria_gasto_id_categoria_gasto_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5206 (class 0 OID 0)
-- Dependencies: 239
-- Name: categoria_gasto_id_categoria_gasto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categoria_gasto_id_categoria_gasto_seq OWNED BY public.categoria_gasto.id_categoria_gasto;


--
-- TOC entry 228 (class 1259 OID 16465)
-- Name: categoria_producto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.categoria_producto (
    id_categoria_producto integer NOT NULL,
    id_empresa integer NOT NULL,
    nombre character varying(100) NOT NULL,
    descripcion character varying(255)
);


--
-- TOC entry 227 (class 1259 OID 16464)
-- Name: categoria_producto_id_categoria_producto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.categoria_producto_id_categoria_producto_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5207 (class 0 OID 0)
-- Dependencies: 227
-- Name: categoria_producto_id_categoria_producto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.categoria_producto_id_categoria_producto_seq OWNED BY public.categoria_producto.id_categoria_producto;


--
-- TOC entry 226 (class 1259 OID 16446)
-- Name: cliente; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cliente (
    id_cliente integer NOT NULL,
    id_empresa integer NOT NULL,
    tipo_identificacion character varying(20) NOT NULL,
    identificacion character varying(20) NOT NULL,
    nombre_razon_social character varying(255) NOT NULL,
    direccion text,
    telefono character varying(20),
    correo_electronico character varying(150)
);


--
-- TOC entry 225 (class 1259 OID 16445)
-- Name: cliente_id_cliente_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cliente_id_cliente_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5208 (class 0 OID 0)
-- Dependencies: 225
-- Name: cliente_id_cliente_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cliente_id_cliente_seq OWNED BY public.cliente.id_cliente;


--
-- TOC entry 250 (class 1259 OID 16757)
-- Name: consumo_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.consumo_tokens (
    id_consumo_tokens integer NOT NULL,
    id_empresa integer NOT NULL,
    modelo_ia character varying(50) NOT NULL,
    tokens_prompt integer DEFAULT 0 NOT NULL,
    tokens_completado integer DEFAULT 0 NOT NULL,
    costo_estimado numeric(10,6) DEFAULT 0.000000 NOT NULL,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- TOC entry 249 (class 1259 OID 16756)
-- Name: consumo_tokens_id_consumo_tokens_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.consumo_tokens_id_consumo_tokens_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5209 (class 0 OID 0)
-- Dependencies: 249
-- Name: consumo_tokens_id_consumo_tokens_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.consumo_tokens_id_consumo_tokens_seq OWNED BY public.consumo_tokens.id_consumo_tokens;


--
-- TOC entry 246 (class 1259 OID 16701)
-- Name: dashboard_financiero; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.dashboard_financiero (
    id_dashboard integer NOT NULL,
    id_empresa integer NOT NULL,
    periodo character varying(7) NOT NULL,
    ingresos_totales numeric(12,2) DEFAULT 0.00 NOT NULL,
    gastos_totales numeric(12,2) DEFAULT 0.00 NOT NULL,
    utilidad_neta numeric(12,2) DEFAULT 0.00 NOT NULL,
    ventas_registradas integer DEFAULT 0 NOT NULL,
    gastos_por_categoria jsonb,
    estado_inventario jsonb,
    productos_stock_bajo integer DEFAULT 0 NOT NULL,
    fecha_calculo timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- TOC entry 245 (class 1259 OID 16700)
-- Name: dashboard_financiero_id_dashboard_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.dashboard_financiero_id_dashboard_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5210 (class 0 OID 0)
-- Dependencies: 245
-- Name: dashboard_financiero_id_dashboard_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.dashboard_financiero_id_dashboard_seq OWNED BY public.dashboard_financiero.id_dashboard;


--
-- TOC entry 236 (class 1259 OID 16578)
-- Name: detalle_venta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalle_venta (
    id_detalle_venta integer NOT NULL,
    id_venta integer NOT NULL,
    id_producto integer,
    descripcion_libre character varying(255),
    cantidad numeric(10,2) NOT NULL,
    precio_unitario numeric(10,2) NOT NULL,
    descuento numeric(10,2) DEFAULT 0.00 NOT NULL,
    subtotal numeric(10,2) NOT NULL
);


--
-- TOC entry 235 (class 1259 OID 16577)
-- Name: detalle_venta_id_detalle_venta_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.detalle_venta_id_detalle_venta_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5211 (class 0 OID 0)
-- Dependencies: 235
-- Name: detalle_venta_id_detalle_venta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.detalle_venta_id_detalle_venta_seq OWNED BY public.detalle_venta.id_detalle_venta;


--
-- TOC entry 220 (class 1259 OID 16389)
-- Name: empresa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.empresa (
    id_empresa integer NOT NULL,
    razon_social character varying(255) NOT NULL,
    nombre_comercial character varying(255),
    ruc character varying(13) NOT NULL,
    actividad_economica character varying(255),
    direccion text,
    correo_electronico character varying(150) NOT NULL,
    datos_facturacion_electronica jsonb,
    firma_electronica character varying(255),
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- TOC entry 219 (class 1259 OID 16388)
-- Name: empresa_id_empresa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.empresa_id_empresa_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5212 (class 0 OID 0)
-- Dependencies: 219
-- Name: empresa_id_empresa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.empresa_id_empresa_seq OWNED BY public.empresa.id_empresa;


--
-- TOC entry 234 (class 1259 OID 16550)
-- Name: factura; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.factura (
    id_factura integer NOT NULL,
    id_venta integer NOT NULL,
    numero_comprobante character varying(17) NOT NULL,
    clave_acceso character varying(49),
    estado_autorizacion character varying(30) NOT NULL,
    subtotal numeric(10,2) NOT NULL,
    impuestos numeric(10,2) NOT NULL,
    total numeric(10,2) NOT NULL,
    fecha_emision timestamp without time zone NOT NULL,
    xml_firmado text,
    pdf_ride_path character varying(255)
);


--
-- TOC entry 233 (class 1259 OID 16549)
-- Name: factura_id_factura_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.factura_id_factura_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5213 (class 0 OID 0)
-- Dependencies: 233
-- Name: factura_id_factura_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.factura_id_factura_seq OWNED BY public.factura.id_factura;


--
-- TOC entry 242 (class 1259 OID 16637)
-- Name: gasto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gasto (
    id_gasto integer NOT NULL,
    id_empresa integer NOT NULL,
    id_categoria_gasto integer NOT NULL,
    id_usuario integer NOT NULL,
    id_proveedor integer,
    monto numeric(10,2) NOT NULL,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    numero_comprobante character varying(50),
    concepto text NOT NULL,
    metodo_pago character varying(50) NOT NULL,
    estado character varying(20) DEFAULT 'CONFIRMADO'::character varying NOT NULL
);


--
-- TOC entry 241 (class 1259 OID 16636)
-- Name: gasto_id_gasto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.gasto_id_gasto_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5214 (class 0 OID 0)
-- Dependencies: 241
-- Name: gasto_id_gasto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.gasto_id_gasto_seq OWNED BY public.gasto.id_gasto;


--
-- TOC entry 244 (class 1259 OID 16677)
-- Name: movimiento_inventario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimiento_inventario (
    id_movimiento integer NOT NULL,
    id_producto integer NOT NULL,
    id_usuario integer NOT NULL,
    tipo_movimiento character varying(30) NOT NULL,
    cantidad numeric(10,2) NOT NULL,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    motivo character varying(255)
);


--
-- TOC entry 243 (class 1259 OID 16676)
-- Name: movimiento_inventario_id_movimiento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movimiento_inventario_id_movimiento_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5215 (class 0 OID 0)
-- Dependencies: 243
-- Name: movimiento_inventario_id_movimiento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.movimiento_inventario_id_movimiento_seq OWNED BY public.movimiento_inventario.id_movimiento;


--
-- TOC entry 230 (class 1259 OID 16480)
-- Name: producto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.producto (
    id_producto integer NOT NULL,
    id_empresa integer NOT NULL,
    id_categoria_producto integer NOT NULL,
    codigo_principal character varying(50) NOT NULL,
    nombre character varying(150) NOT NULL,
    descripcion text,
    precio_compra numeric(10,2) DEFAULT 0.00 NOT NULL,
    precio_venta numeric(10,2) DEFAULT 0.00 NOT NULL,
    stock_actual numeric(10,2) DEFAULT 0.00 NOT NULL,
    stock_minimo numeric(10,2),
    unidad_medida character varying(20) DEFAULT 'UNIDAD'::character varying NOT NULL,
    tipo character varying(20) DEFAULT 'VENTA'::character varying NOT NULL,
    aplica_iva boolean DEFAULT true NOT NULL
);


--
-- TOC entry 229 (class 1259 OID 16479)
-- Name: producto_id_producto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.producto_id_producto_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5216 (class 0 OID 0)
-- Dependencies: 229
-- Name: producto_id_producto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.producto_id_producto_seq OWNED BY public.producto.id_producto;


--
-- TOC entry 238 (class 1259 OID 16602)
-- Name: proveedor; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.proveedor (
    id_proveedor integer NOT NULL,
    id_empresa integer NOT NULL,
    ruc_identificacion character varying(20) NOT NULL,
    razon_social character varying(255) NOT NULL,
    telefono character varying(20),
    correo_electronico character varying(150),
    direccion text
);


--
-- TOC entry 237 (class 1259 OID 16601)
-- Name: proveedor_id_proveedor_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.proveedor_id_proveedor_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5217 (class 0 OID 0)
-- Dependencies: 237
-- Name: proveedor_id_proveedor_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.proveedor_id_proveedor_seq OWNED BY public.proveedor.id_proveedor;


--
-- TOC entry 252 (class 1259 OID 16780)
-- Name: recomendacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.recomendacion (
    id_recomendacion integer NOT NULL,
    id_empresa integer NOT NULL,
    tipo character varying(50) NOT NULL,
    descripcion text NOT NULL,
    datos_utilizados jsonb,
    estado character varying(20) DEFAULT 'ACTIVA'::character varying NOT NULL,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- TOC entry 251 (class 1259 OID 16779)
-- Name: recomendacion_id_recomendacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.recomendacion_id_recomendacion_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5218 (class 0 OID 0)
-- Dependencies: 251
-- Name: recomendacion_id_recomendacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.recomendacion_id_recomendacion_seq OWNED BY public.recomendacion.id_recomendacion;


--
-- TOC entry 222 (class 1259 OID 16406)
-- Name: rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol (
    id_rol integer NOT NULL,
    nombre character varying(50) NOT NULL,
    descripcion character varying(255)
);


--
-- TOC entry 221 (class 1259 OID 16405)
-- Name: rol_id_rol_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_id_rol_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5219 (class 0 OID 0)
-- Dependencies: 221
-- Name: rol_id_rol_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_id_rol_seq OWNED BY public.rol.id_rol;


--
-- TOC entry 224 (class 1259 OID 16417)
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id_usuario integer NOT NULL,
    id_empresa integer NOT NULL,
    id_rol integer NOT NULL,
    nombre character varying(150) NOT NULL,
    correo_electronico character varying(150) NOT NULL,
    contrasena_hash character varying(255) NOT NULL,
    estado character varying(20) DEFAULT 'ACTIVO'::character varying NOT NULL
);


--
-- TOC entry 223 (class 1259 OID 16416)
-- Name: usuario_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_usuario_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5220 (class 0 OID 0)
-- Dependencies: 223
-- Name: usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_usuario_seq OWNED BY public.usuario.id_usuario;


--
-- TOC entry 232 (class 1259 OID 16516)
-- Name: venta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.venta (
    id_venta integer NOT NULL,
    id_empresa integer NOT NULL,
    id_usuario integer NOT NULL,
    id_cliente integer,
    fecha timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    subtotal numeric(10,2) NOT NULL,
    iva numeric(10,2) NOT NULL,
    monto_total numeric(10,2) NOT NULL,
    tipo_origen character varying(30) NOT NULL,
    metodo_pago character varying(50) NOT NULL,
    observacion character varying(255),
    estado character varying(20) DEFAULT 'COMPLETADA'::character varying NOT NULL
);


--
-- TOC entry 231 (class 1259 OID 16515)
-- Name: venta_id_venta_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.venta_id_venta_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- TOC entry 5221 (class 0 OID 0)
-- Dependencies: 231
-- Name: venta_id_venta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.venta_id_venta_seq OWNED BY public.venta.id_venta;


--
-- TOC entry 4971 (class 2604 OID 16733)
-- Name: accion_ia id_accion_ia; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accion_ia ALTER COLUMN id_accion_ia SET DEFAULT nextval('public.accion_ia_id_accion_ia_seq'::regclass);


--
-- TOC entry 4957 (class 2604 OID 16623)
-- Name: categoria_gasto id_categoria_gasto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_gasto ALTER COLUMN id_categoria_gasto SET DEFAULT nextval('public.categoria_gasto_id_categoria_gasto_seq'::regclass);


--
-- TOC entry 4942 (class 2604 OID 16468)
-- Name: categoria_producto id_categoria_producto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_producto ALTER COLUMN id_categoria_producto SET DEFAULT nextval('public.categoria_producto_id_categoria_producto_seq'::regclass);


--
-- TOC entry 4941 (class 2604 OID 16449)
-- Name: cliente id_cliente; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente ALTER COLUMN id_cliente SET DEFAULT nextval('public.cliente_id_cliente_seq'::regclass);


--
-- TOC entry 4974 (class 2604 OID 16760)
-- Name: consumo_tokens id_consumo_tokens; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consumo_tokens ALTER COLUMN id_consumo_tokens SET DEFAULT nextval('public.consumo_tokens_id_consumo_tokens_seq'::regclass);


--
-- TOC entry 4964 (class 2604 OID 16704)
-- Name: dashboard_financiero id_dashboard; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboard_financiero ALTER COLUMN id_dashboard SET DEFAULT nextval('public.dashboard_financiero_id_dashboard_seq'::regclass);


--
-- TOC entry 4954 (class 2604 OID 16581)
-- Name: detalle_venta id_detalle_venta; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_venta ALTER COLUMN id_detalle_venta SET DEFAULT nextval('public.detalle_venta_id_detalle_venta_seq'::regclass);


--
-- TOC entry 4936 (class 2604 OID 16392)
-- Name: empresa id_empresa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresa ALTER COLUMN id_empresa SET DEFAULT nextval('public.empresa_id_empresa_seq'::regclass);


--
-- TOC entry 4953 (class 2604 OID 16553)
-- Name: factura id_factura; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura ALTER COLUMN id_factura SET DEFAULT nextval('public.factura_id_factura_seq'::regclass);


--
-- TOC entry 4959 (class 2604 OID 16640)
-- Name: gasto id_gasto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto ALTER COLUMN id_gasto SET DEFAULT nextval('public.gasto_id_gasto_seq'::regclass);


--
-- TOC entry 4962 (class 2604 OID 16680)
-- Name: movimiento_inventario id_movimiento; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_inventario ALTER COLUMN id_movimiento SET DEFAULT nextval('public.movimiento_inventario_id_movimiento_seq'::regclass);


--
-- TOC entry 4943 (class 2604 OID 16483)
-- Name: producto id_producto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto ALTER COLUMN id_producto SET DEFAULT nextval('public.producto_id_producto_seq'::regclass);


--
-- TOC entry 4956 (class 2604 OID 16605)
-- Name: proveedor id_proveedor; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor ALTER COLUMN id_proveedor SET DEFAULT nextval('public.proveedor_id_proveedor_seq'::regclass);


--
-- TOC entry 4979 (class 2604 OID 16783)
-- Name: recomendacion id_recomendacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recomendacion ALTER COLUMN id_recomendacion SET DEFAULT nextval('public.recomendacion_id_recomendacion_seq'::regclass);


--
-- TOC entry 4938 (class 2604 OID 16409)
-- Name: rol id_rol; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol ALTER COLUMN id_rol SET DEFAULT nextval('public.rol_id_rol_seq'::regclass);


--
-- TOC entry 4939 (class 2604 OID 16420)
-- Name: usuario id_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id_usuario SET DEFAULT nextval('public.usuario_id_usuario_seq'::regclass);


--
-- TOC entry 4950 (class 2604 OID 16519)
-- Name: venta id_venta; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta ALTER COLUMN id_venta SET DEFAULT nextval('public.venta_id_venta_seq'::regclass);


--
-- TOC entry 5023 (class 2606 OID 16745)
-- Name: accion_ia accion_ia_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accion_ia
    ADD CONSTRAINT accion_ia_pkey PRIMARY KEY (id_accion_ia);


--
-- TOC entry 5015 (class 2606 OID 16630)
-- Name: categoria_gasto categoria_gasto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_gasto
    ADD CONSTRAINT categoria_gasto_pkey PRIMARY KEY (id_categoria_gasto);


--
-- TOC entry 4997 (class 2606 OID 16473)
-- Name: categoria_producto categoria_producto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_producto
    ADD CONSTRAINT categoria_producto_pkey PRIMARY KEY (id_categoria_producto);


--
-- TOC entry 4995 (class 2606 OID 16458)
-- Name: cliente cliente_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente
    ADD CONSTRAINT cliente_pkey PRIMARY KEY (id_cliente);


--
-- TOC entry 5025 (class 2606 OID 16773)
-- Name: consumo_tokens consumo_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consumo_tokens
    ADD CONSTRAINT consumo_tokens_pkey PRIMARY KEY (id_consumo_tokens);


--
-- TOC entry 5021 (class 2606 OID 16723)
-- Name: dashboard_financiero dashboard_financiero_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboard_financiero
    ADD CONSTRAINT dashboard_financiero_pkey PRIMARY KEY (id_dashboard);


--
-- TOC entry 5011 (class 2606 OID 16590)
-- Name: detalle_venta detalle_venta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_venta
    ADD CONSTRAINT detalle_venta_pkey PRIMARY KEY (id_detalle_venta);


--
-- TOC entry 4983 (class 2606 OID 16402)
-- Name: empresa empresa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresa
    ADD CONSTRAINT empresa_pkey PRIMARY KEY (id_empresa);


--
-- TOC entry 4985 (class 2606 OID 16404)
-- Name: empresa empresa_ruc_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.empresa
    ADD CONSTRAINT empresa_ruc_key UNIQUE (ruc);


--
-- TOC entry 5003 (class 2606 OID 16571)
-- Name: factura factura_clave_acceso_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura
    ADD CONSTRAINT factura_clave_acceso_key UNIQUE (clave_acceso);


--
-- TOC entry 5005 (class 2606 OID 16567)
-- Name: factura factura_id_venta_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura
    ADD CONSTRAINT factura_id_venta_key UNIQUE (id_venta);


--
-- TOC entry 5007 (class 2606 OID 16569)
-- Name: factura factura_numero_comprobante_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura
    ADD CONSTRAINT factura_numero_comprobante_key UNIQUE (numero_comprobante);


--
-- TOC entry 5009 (class 2606 OID 16565)
-- Name: factura factura_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura
    ADD CONSTRAINT factura_pkey PRIMARY KEY (id_factura);


--
-- TOC entry 5017 (class 2606 OID 16655)
-- Name: gasto gasto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto
    ADD CONSTRAINT gasto_pkey PRIMARY KEY (id_gasto);


--
-- TOC entry 5019 (class 2606 OID 16689)
-- Name: movimiento_inventario movimiento_inventario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_inventario
    ADD CONSTRAINT movimiento_inventario_pkey PRIMARY KEY (id_movimiento);


--
-- TOC entry 4999 (class 2606 OID 16504)
-- Name: producto producto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto
    ADD CONSTRAINT producto_pkey PRIMARY KEY (id_producto);


--
-- TOC entry 5013 (class 2606 OID 16613)
-- Name: proveedor proveedor_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor
    ADD CONSTRAINT proveedor_pkey PRIMARY KEY (id_proveedor);


--
-- TOC entry 5027 (class 2606 OID 16795)
-- Name: recomendacion recomendacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recomendacion
    ADD CONSTRAINT recomendacion_pkey PRIMARY KEY (id_recomendacion);


--
-- TOC entry 4987 (class 2606 OID 16415)
-- Name: rol rol_nombre_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_nombre_key UNIQUE (nombre);


--
-- TOC entry 4989 (class 2606 OID 16413)
-- Name: rol rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol
    ADD CONSTRAINT rol_pkey PRIMARY KEY (id_rol);


--
-- TOC entry 4991 (class 2606 OID 16434)
-- Name: usuario usuario_correo_electronico_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_correo_electronico_key UNIQUE (correo_electronico);


--
-- TOC entry 4993 (class 2606 OID 16432)
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario);


--
-- TOC entry 5001 (class 2606 OID 16533)
-- Name: venta venta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT venta_pkey PRIMARY KEY (id_venta);


--
-- TOC entry 5049 (class 2606 OID 16746)
-- Name: accion_ia accion_ia_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accion_ia
    ADD CONSTRAINT accion_ia_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5050 (class 2606 OID 16751)
-- Name: accion_ia accion_ia_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.accion_ia
    ADD CONSTRAINT accion_ia_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5041 (class 2606 OID 16631)
-- Name: categoria_gasto categoria_gasto_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_gasto
    ADD CONSTRAINT categoria_gasto_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5031 (class 2606 OID 16474)
-- Name: categoria_producto categoria_producto_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.categoria_producto
    ADD CONSTRAINT categoria_producto_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5030 (class 2606 OID 16459)
-- Name: cliente cliente_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente
    ADD CONSTRAINT cliente_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5051 (class 2606 OID 16774)
-- Name: consumo_tokens consumo_tokens_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.consumo_tokens
    ADD CONSTRAINT consumo_tokens_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5048 (class 2606 OID 16724)
-- Name: dashboard_financiero dashboard_financiero_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.dashboard_financiero
    ADD CONSTRAINT dashboard_financiero_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5038 (class 2606 OID 16596)
-- Name: detalle_venta detalle_venta_id_producto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_venta
    ADD CONSTRAINT detalle_venta_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.producto(id_producto) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5039 (class 2606 OID 16591)
-- Name: detalle_venta detalle_venta_id_venta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_venta
    ADD CONSTRAINT detalle_venta_id_venta_fkey FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5037 (class 2606 OID 16572)
-- Name: factura factura_id_venta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura
    ADD CONSTRAINT factura_id_venta_fkey FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5042 (class 2606 OID 16661)
-- Name: gasto gasto_id_categoria_gasto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto
    ADD CONSTRAINT gasto_id_categoria_gasto_fkey FOREIGN KEY (id_categoria_gasto) REFERENCES public.categoria_gasto(id_categoria_gasto) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 5043 (class 2606 OID 16656)
-- Name: gasto gasto_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto
    ADD CONSTRAINT gasto_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5044 (class 2606 OID 16671)
-- Name: gasto gasto_id_proveedor_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto
    ADD CONSTRAINT gasto_id_proveedor_fkey FOREIGN KEY (id_proveedor) REFERENCES public.proveedor(id_proveedor) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5045 (class 2606 OID 16666)
-- Name: gasto gasto_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gasto
    ADD CONSTRAINT gasto_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 5046 (class 2606 OID 16690)
-- Name: movimiento_inventario movimiento_inventario_id_producto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_inventario
    ADD CONSTRAINT movimiento_inventario_id_producto_fkey FOREIGN KEY (id_producto) REFERENCES public.producto(id_producto) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5047 (class 2606 OID 16695)
-- Name: movimiento_inventario movimiento_inventario_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_inventario
    ADD CONSTRAINT movimiento_inventario_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 5032 (class 2606 OID 16510)
-- Name: producto producto_id_categoria_producto_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto
    ADD CONSTRAINT producto_id_categoria_producto_fkey FOREIGN KEY (id_categoria_producto) REFERENCES public.categoria_producto(id_categoria_producto) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 5033 (class 2606 OID 16505)
-- Name: producto producto_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.producto
    ADD CONSTRAINT producto_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5040 (class 2606 OID 16614)
-- Name: proveedor proveedor_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.proveedor
    ADD CONSTRAINT proveedor_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5052 (class 2606 OID 16796)
-- Name: recomendacion recomendacion_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.recomendacion
    ADD CONSTRAINT recomendacion_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5028 (class 2606 OID 16435)
-- Name: usuario usuario_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5029 (class 2606 OID 16440)
-- Name: usuario usuario_id_rol_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_id_rol_fkey FOREIGN KEY (id_rol) REFERENCES public.rol(id_rol) ON UPDATE CASCADE ON DELETE RESTRICT;


--
-- TOC entry 5034 (class 2606 OID 16544)
-- Name: venta venta_id_cliente_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT venta_id_cliente_fkey FOREIGN KEY (id_cliente) REFERENCES public.cliente(id_cliente) ON UPDATE CASCADE ON DELETE SET NULL;


--
-- TOC entry 5035 (class 2606 OID 16534)
-- Name: venta venta_id_empresa_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT venta_id_empresa_fkey FOREIGN KEY (id_empresa) REFERENCES public.empresa(id_empresa) ON UPDATE CASCADE ON DELETE CASCADE;


--
-- TOC entry 5036 (class 2606 OID 16539)
-- Name: venta venta_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT venta_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON UPDATE CASCADE ON DELETE RESTRICT;


-- Completed on 2026-10-18 21:57:18
--
-- PostgreSQL database dump complete
--