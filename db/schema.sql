--
-- PostgreSQL database dump
--

\restrict bpWfaEk3sjRp1fnHJuEvC4oPk319WybFgkvieofPxyEXZyfQMO8T9T1dH9ThrY5

-- Dumped from database version 16.14
-- Dumped by pg_dump version 16.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
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
-- Name: activities; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.activities (
    activity_id character varying NOT NULL,
    deal_id character varying NOT NULL,
    activity_type character varying,
    direction character varying,
    subject text,
    responsible_user_id character varying,
    completed boolean,
    deadline_at timestamp with time zone,
    completed_at timestamp with time zone,
    has_quality_issue boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_activity_type CHECK (((activity_type)::text = ANY ((ARRAY['call'::character varying, 'email'::character varying, 'task'::character varying])::text[])))
);


ALTER TABLE public.activities OWNER TO termosphere;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO termosphere;

--
-- Name: companies; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.companies (
    company_id character varying NOT NULL,
    name text,
    inn character varying,
    city text,
    industry text,
    created_at timestamp with time zone,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.companies OWNER TO termosphere;

--
-- Name: contacts; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.contacts (
    contact_id character varying NOT NULL,
    company_id character varying,
    name text,
    phone character varying,
    email text,
    created_at timestamp with time zone,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.contacts OWNER TO termosphere;

--
-- Name: data_quality_issues; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.data_quality_issues (
    id integer NOT NULL,
    entity character varying NOT NULL,
    entity_id character varying,
    issue_type character varying NOT NULL,
    action character varying NOT NULL,
    details text,
    detected_at timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ck_dqi_action CHECK (((action)::text = ANY ((ARRAY['fixed'::character varying, 'quarantined'::character varying, 'flagged'::character varying])::text[])))
);


ALTER TABLE public.data_quality_issues OWNER TO termosphere;

--
-- Name: data_quality_issues_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.data_quality_issues_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.data_quality_issues_id_seq OWNER TO termosphere;

--
-- Name: data_quality_issues_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.data_quality_issues_id_seq OWNED BY public.data_quality_issues.id;


--
-- Name: deal_products; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.deal_products (
    id integer NOT NULL,
    deal_id character varying NOT NULL,
    product_id character varying NOT NULL,
    quantity numeric(14,2),
    unit_price numeric(14,2),
    discount numeric(14,2) DEFAULT '0'::numeric NOT NULL,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.deal_products OWNER TO termosphere;

--
-- Name: deal_products_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.deal_products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.deal_products_id_seq OWNER TO termosphere;

--
-- Name: deal_products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.deal_products_id_seq OWNED BY public.deal_products.id;


--
-- Name: deals; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.deals (
    deal_id character varying NOT NULL,
    title text,
    created_at timestamp with time zone,
    updated_at timestamp with time zone,
    closed_at timestamp with time zone,
    custom_deadline date,
    stage_id character varying,
    manager_id character varying,
    company_id character varying,
    contact_id character varying,
    source_id integer,
    expected_amount numeric(14,2),
    currency character varying DEFAULT 'RUB'::character varying NOT NULL,
    lost_reason text,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.deals OWNER TO termosphere;

--
-- Name: marketing_costs; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.marketing_costs (
    id integer NOT NULL,
    cost_date date,
    source_id integer,
    campaign text,
    cost_amount numeric(14,2),
    currency character varying DEFAULT 'RUB'::character varying NOT NULL,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.marketing_costs OWNER TO termosphere;

--
-- Name: marketing_costs_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.marketing_costs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.marketing_costs_id_seq OWNER TO termosphere;

--
-- Name: marketing_costs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.marketing_costs_id_seq OWNED BY public.marketing_costs.id;


--
-- Name: payments; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.payments (
    payment_id character varying NOT NULL,
    deal_id character varying NOT NULL,
    payment_date date,
    amount numeric(14,2),
    payment_type character varying,
    status character varying,
    has_quality_issue boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_payment_status CHECK (((status)::text = ANY ((ARRAY['paid'::character varying, 'pending'::character varying])::text[]))),
    CONSTRAINT ck_payment_type CHECK (((payment_type)::text = ANY ((ARRAY['prepayment'::character varying, 'full'::character varying, 'correction'::character varying, 'unknown'::character varying])::text[])))
);


ALTER TABLE public.payments OWNER TO termosphere;

--
-- Name: pipeline_stages; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.pipeline_stages (
    stage_id character varying NOT NULL,
    pipeline_id character varying,
    stage_name text,
    sort_order integer,
    is_final boolean,
    is_success boolean
);


ALTER TABLE public.pipeline_stages OWNER TO termosphere;

--
-- Name: production_orders; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.production_orders (
    production_order_id character varying NOT NULL,
    deal_id character varying NOT NULL,
    created_at timestamp with time zone,
    planned_finish_at date,
    actual_finish_at date,
    status character varying,
    workshop text,
    has_quality_issue boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_production_status CHECK (((status)::text = ANY ((ARRAY['planned'::character varying, 'in_progress'::character varying, 'done'::character varying])::text[])))
);


ALTER TABLE public.production_orders OWNER TO termosphere;

--
-- Name: products; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.products (
    product_id character varying NOT NULL,
    sku character varying,
    name text,
    category text,
    cost_price numeric(14,2),
    is_active boolean,
    canonical_id character varying,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.products OWNER TO termosphere;

--
-- Name: raw_activities; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_activities (
    id integer NOT NULL,
    activity_id text,
    deal_id text,
    activity_type text,
    direction text,
    subject text,
    responsible_user_id text,
    completed text,
    deadline_at text,
    completed_at text
);


ALTER TABLE public.raw_activities OWNER TO termosphere;

--
-- Name: raw_activities_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_activities_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_activities_id_seq OWNER TO termosphere;

--
-- Name: raw_activities_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_activities_id_seq OWNED BY public.raw_activities.id;


--
-- Name: raw_companies; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_companies (
    id integer NOT NULL,
    company_id text,
    name text,
    inn text,
    city text,
    industry text,
    created_at text
);


ALTER TABLE public.raw_companies OWNER TO termosphere;

--
-- Name: raw_companies_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_companies_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_companies_id_seq OWNER TO termosphere;

--
-- Name: raw_companies_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_companies_id_seq OWNED BY public.raw_companies.id;


--
-- Name: raw_contacts; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_contacts (
    id integer NOT NULL,
    contact_id text,
    company_id text,
    name text,
    phone text,
    email text,
    created_at text
);


ALTER TABLE public.raw_contacts OWNER TO termosphere;

--
-- Name: raw_contacts_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_contacts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_contacts_id_seq OWNER TO termosphere;

--
-- Name: raw_contacts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_contacts_id_seq OWNED BY public.raw_contacts.id;


--
-- Name: raw_deal_products; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_deal_products (
    id integer NOT NULL,
    deal_id text,
    product_id text,
    quantity text,
    unit_price text,
    discount text
);


ALTER TABLE public.raw_deal_products OWNER TO termosphere;

--
-- Name: raw_deal_products_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_deal_products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_deal_products_id_seq OWNER TO termosphere;

--
-- Name: raw_deal_products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_deal_products_id_seq OWNED BY public.raw_deal_products.id;


--
-- Name: raw_deals; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_deals (
    id integer NOT NULL,
    deal_id text,
    title text,
    created_at text,
    updated_at text,
    stage_id text,
    manager_id text,
    company_id text,
    contact_id text,
    source text,
    expected_amount text,
    currency text,
    closed_at text,
    lost_reason text,
    custom_deadline text
);


ALTER TABLE public.raw_deals OWNER TO termosphere;

--
-- Name: raw_deals_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_deals_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_deals_id_seq OWNER TO termosphere;

--
-- Name: raw_deals_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_deals_id_seq OWNED BY public.raw_deals.id;


--
-- Name: raw_marketing_costs; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_marketing_costs (
    id integer NOT NULL,
    cost_date text,
    source text,
    campaign text,
    cost_amount text,
    currency text
);


ALTER TABLE public.raw_marketing_costs OWNER TO termosphere;

--
-- Name: raw_marketing_costs_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_marketing_costs_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_marketing_costs_id_seq OWNER TO termosphere;

--
-- Name: raw_marketing_costs_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_marketing_costs_id_seq OWNED BY public.raw_marketing_costs.id;


--
-- Name: raw_payments; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_payments (
    id integer NOT NULL,
    payment_id text,
    deal_id text,
    payment_date text,
    amount text,
    payment_type text,
    status text
);


ALTER TABLE public.raw_payments OWNER TO termosphere;

--
-- Name: raw_payments_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_payments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_payments_id_seq OWNER TO termosphere;

--
-- Name: raw_payments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_payments_id_seq OWNED BY public.raw_payments.id;


--
-- Name: raw_pipeline_stages; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_pipeline_stages (
    id integer NOT NULL,
    pipeline_id text,
    stage_id text,
    stage_name text,
    sort_order text,
    is_final text,
    is_success text
);


ALTER TABLE public.raw_pipeline_stages OWNER TO termosphere;

--
-- Name: raw_pipeline_stages_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_pipeline_stages_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_pipeline_stages_id_seq OWNER TO termosphere;

--
-- Name: raw_pipeline_stages_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_pipeline_stages_id_seq OWNED BY public.raw_pipeline_stages.id;


--
-- Name: raw_production_orders; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_production_orders (
    id integer NOT NULL,
    production_order_id text,
    deal_id text,
    created_at text,
    planned_finish_at text,
    actual_finish_at text,
    status text,
    workshop text
);


ALTER TABLE public.raw_production_orders OWNER TO termosphere;

--
-- Name: raw_production_orders_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_production_orders_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_production_orders_id_seq OWNER TO termosphere;

--
-- Name: raw_production_orders_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_production_orders_id_seq OWNED BY public.raw_production_orders.id;


--
-- Name: raw_products; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_products (
    id integer NOT NULL,
    product_id text,
    sku text,
    name text,
    category text,
    cost_price text,
    is_active text
);


ALTER TABLE public.raw_products OWNER TO termosphere;

--
-- Name: raw_products_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_products_id_seq OWNER TO termosphere;

--
-- Name: raw_products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_products_id_seq OWNED BY public.raw_products.id;


--
-- Name: raw_shipments; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_shipments (
    id integer NOT NULL,
    shipment_id text,
    deal_id text,
    planned_date text,
    actual_date text,
    status text
);


ALTER TABLE public.raw_shipments OWNER TO termosphere;

--
-- Name: raw_shipments_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_shipments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_shipments_id_seq OWNER TO termosphere;

--
-- Name: raw_shipments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_shipments_id_seq OWNED BY public.raw_shipments.id;


--
-- Name: raw_stage_history; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_stage_history (
    id integer NOT NULL,
    event_id text,
    deal_id text,
    old_stage_id text,
    new_stage_id text,
    changed_at text,
    changed_by_id text
);


ALTER TABLE public.raw_stage_history OWNER TO termosphere;

--
-- Name: raw_stage_history_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_stage_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_stage_history_id_seq OWNER TO termosphere;

--
-- Name: raw_stage_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_stage_history_id_seq OWNED BY public.raw_stage_history.id;


--
-- Name: raw_users; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.raw_users (
    id integer NOT NULL,
    user_id text,
    name text,
    role text,
    active text,
    department text,
    email text
);


ALTER TABLE public.raw_users OWNER TO termosphere;

--
-- Name: raw_users_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.raw_users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.raw_users_id_seq OWNER TO termosphere;

--
-- Name: raw_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.raw_users_id_seq OWNED BY public.raw_users.id;


--
-- Name: shipments; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.shipments (
    shipment_id character varying NOT NULL,
    deal_id character varying NOT NULL,
    planned_date date,
    actual_date date,
    status character varying,
    has_quality_issue boolean DEFAULT false NOT NULL,
    CONSTRAINT ck_shipment_status CHECK (((status)::text = ANY ((ARRAY['planned'::character varying, 'shipped'::character varying])::text[])))
);


ALTER TABLE public.shipments OWNER TO termosphere;

--
-- Name: sources; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.sources (
    id integer NOT NULL,
    code character varying NOT NULL,
    name character varying
);


ALTER TABLE public.sources OWNER TO termosphere;

--
-- Name: sources_id_seq; Type: SEQUENCE; Schema: public; Owner: termosphere
--

CREATE SEQUENCE public.sources_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.sources_id_seq OWNER TO termosphere;

--
-- Name: sources_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: termosphere
--

ALTER SEQUENCE public.sources_id_seq OWNED BY public.sources.id;


--
-- Name: stage_history; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.stage_history (
    event_id character varying NOT NULL,
    deal_id character varying NOT NULL,
    old_stage_id character varying,
    new_stage_id character varying,
    changed_at timestamp with time zone,
    changed_by_id character varying,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.stage_history OWNER TO termosphere;

--
-- Name: users; Type: TABLE; Schema: public; Owner: termosphere
--

CREATE TABLE public.users (
    user_id character varying NOT NULL,
    name text,
    role text,
    active boolean,
    department text,
    email text,
    has_quality_issue boolean DEFAULT false NOT NULL
);


ALTER TABLE public.users OWNER TO termosphere;

--
-- Name: data_quality_issues id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.data_quality_issues ALTER COLUMN id SET DEFAULT nextval('public.data_quality_issues_id_seq'::regclass);


--
-- Name: deal_products id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deal_products ALTER COLUMN id SET DEFAULT nextval('public.deal_products_id_seq'::regclass);


--
-- Name: marketing_costs id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.marketing_costs ALTER COLUMN id SET DEFAULT nextval('public.marketing_costs_id_seq'::regclass);


--
-- Name: raw_activities id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_activities ALTER COLUMN id SET DEFAULT nextval('public.raw_activities_id_seq'::regclass);


--
-- Name: raw_companies id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_companies ALTER COLUMN id SET DEFAULT nextval('public.raw_companies_id_seq'::regclass);


--
-- Name: raw_contacts id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_contacts ALTER COLUMN id SET DEFAULT nextval('public.raw_contacts_id_seq'::regclass);


--
-- Name: raw_deal_products id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_deal_products ALTER COLUMN id SET DEFAULT nextval('public.raw_deal_products_id_seq'::regclass);


--
-- Name: raw_deals id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_deals ALTER COLUMN id SET DEFAULT nextval('public.raw_deals_id_seq'::regclass);


--
-- Name: raw_marketing_costs id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_marketing_costs ALTER COLUMN id SET DEFAULT nextval('public.raw_marketing_costs_id_seq'::regclass);


--
-- Name: raw_payments id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_payments ALTER COLUMN id SET DEFAULT nextval('public.raw_payments_id_seq'::regclass);


--
-- Name: raw_pipeline_stages id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_pipeline_stages ALTER COLUMN id SET DEFAULT nextval('public.raw_pipeline_stages_id_seq'::regclass);


--
-- Name: raw_production_orders id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_production_orders ALTER COLUMN id SET DEFAULT nextval('public.raw_production_orders_id_seq'::regclass);


--
-- Name: raw_products id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_products ALTER COLUMN id SET DEFAULT nextval('public.raw_products_id_seq'::regclass);


--
-- Name: raw_shipments id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_shipments ALTER COLUMN id SET DEFAULT nextval('public.raw_shipments_id_seq'::regclass);


--
-- Name: raw_stage_history id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_stage_history ALTER COLUMN id SET DEFAULT nextval('public.raw_stage_history_id_seq'::regclass);


--
-- Name: raw_users id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_users ALTER COLUMN id SET DEFAULT nextval('public.raw_users_id_seq'::regclass);


--
-- Name: sources id; Type: DEFAULT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.sources ALTER COLUMN id SET DEFAULT nextval('public.sources_id_seq'::regclass);


--
-- Name: activities activities_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_pkey PRIMARY KEY (activity_id);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: companies companies_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.companies
    ADD CONSTRAINT companies_pkey PRIMARY KEY (company_id);


--
-- Name: contacts contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_pkey PRIMARY KEY (contact_id);


--
-- Name: data_quality_issues data_quality_issues_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.data_quality_issues
    ADD CONSTRAINT data_quality_issues_pkey PRIMARY KEY (id);


--
-- Name: deal_products deal_products_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deal_products
    ADD CONSTRAINT deal_products_pkey PRIMARY KEY (id);


--
-- Name: deals deals_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_pkey PRIMARY KEY (deal_id);


--
-- Name: marketing_costs marketing_costs_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.marketing_costs
    ADD CONSTRAINT marketing_costs_pkey PRIMARY KEY (id);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (payment_id);


--
-- Name: pipeline_stages pipeline_stages_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.pipeline_stages
    ADD CONSTRAINT pipeline_stages_pkey PRIMARY KEY (stage_id);


--
-- Name: production_orders production_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.production_orders
    ADD CONSTRAINT production_orders_pkey PRIMARY KEY (production_order_id);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (product_id);


--
-- Name: raw_activities raw_activities_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_activities
    ADD CONSTRAINT raw_activities_pkey PRIMARY KEY (id);


--
-- Name: raw_companies raw_companies_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_companies
    ADD CONSTRAINT raw_companies_pkey PRIMARY KEY (id);


--
-- Name: raw_contacts raw_contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_contacts
    ADD CONSTRAINT raw_contacts_pkey PRIMARY KEY (id);


--
-- Name: raw_deal_products raw_deal_products_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_deal_products
    ADD CONSTRAINT raw_deal_products_pkey PRIMARY KEY (id);


--
-- Name: raw_deals raw_deals_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_deals
    ADD CONSTRAINT raw_deals_pkey PRIMARY KEY (id);


--
-- Name: raw_marketing_costs raw_marketing_costs_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_marketing_costs
    ADD CONSTRAINT raw_marketing_costs_pkey PRIMARY KEY (id);


--
-- Name: raw_payments raw_payments_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_payments
    ADD CONSTRAINT raw_payments_pkey PRIMARY KEY (id);


--
-- Name: raw_pipeline_stages raw_pipeline_stages_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_pipeline_stages
    ADD CONSTRAINT raw_pipeline_stages_pkey PRIMARY KEY (id);


--
-- Name: raw_production_orders raw_production_orders_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_production_orders
    ADD CONSTRAINT raw_production_orders_pkey PRIMARY KEY (id);


--
-- Name: raw_products raw_products_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_products
    ADD CONSTRAINT raw_products_pkey PRIMARY KEY (id);


--
-- Name: raw_shipments raw_shipments_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_shipments
    ADD CONSTRAINT raw_shipments_pkey PRIMARY KEY (id);


--
-- Name: raw_stage_history raw_stage_history_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_stage_history
    ADD CONSTRAINT raw_stage_history_pkey PRIMARY KEY (id);


--
-- Name: raw_users raw_users_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.raw_users
    ADD CONSTRAINT raw_users_pkey PRIMARY KEY (id);


--
-- Name: shipments shipments_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.shipments
    ADD CONSTRAINT shipments_pkey PRIMARY KEY (shipment_id);


--
-- Name: sources sources_code_key; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_code_key UNIQUE (code);


--
-- Name: sources sources_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.sources
    ADD CONSTRAINT sources_pkey PRIMARY KEY (id);


--
-- Name: stage_history stage_history_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.stage_history
    ADD CONSTRAINT stage_history_pkey PRIMARY KEY (event_id);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (user_id);


--
-- Name: activities activities_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: activities activities_responsible_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.activities
    ADD CONSTRAINT activities_responsible_user_id_fkey FOREIGN KEY (responsible_user_id) REFERENCES public.users(user_id);


--
-- Name: contacts contacts_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id);


--
-- Name: deal_products deal_products_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deal_products
    ADD CONSTRAINT deal_products_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: deal_products deal_products_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deal_products
    ADD CONSTRAINT deal_products_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(product_id);


--
-- Name: deals deals_company_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_company_id_fkey FOREIGN KEY (company_id) REFERENCES public.companies(company_id);


--
-- Name: deals deals_contact_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_contact_id_fkey FOREIGN KEY (contact_id) REFERENCES public.contacts(contact_id);


--
-- Name: deals deals_manager_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_manager_id_fkey FOREIGN KEY (manager_id) REFERENCES public.users(user_id);


--
-- Name: deals deals_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id);


--
-- Name: deals deals_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.deals
    ADD CONSTRAINT deals_stage_id_fkey FOREIGN KEY (stage_id) REFERENCES public.pipeline_stages(stage_id);


--
-- Name: marketing_costs marketing_costs_source_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.marketing_costs
    ADD CONSTRAINT marketing_costs_source_id_fkey FOREIGN KEY (source_id) REFERENCES public.sources(id);


--
-- Name: payments payments_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: production_orders production_orders_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.production_orders
    ADD CONSTRAINT production_orders_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: products products_canonical_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_canonical_id_fkey FOREIGN KEY (canonical_id) REFERENCES public.products(product_id);


--
-- Name: shipments shipments_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.shipments
    ADD CONSTRAINT shipments_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: stage_history stage_history_changed_by_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.stage_history
    ADD CONSTRAINT stage_history_changed_by_id_fkey FOREIGN KEY (changed_by_id) REFERENCES public.users(user_id);


--
-- Name: stage_history stage_history_deal_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.stage_history
    ADD CONSTRAINT stage_history_deal_id_fkey FOREIGN KEY (deal_id) REFERENCES public.deals(deal_id);


--
-- Name: stage_history stage_history_new_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.stage_history
    ADD CONSTRAINT stage_history_new_stage_id_fkey FOREIGN KEY (new_stage_id) REFERENCES public.pipeline_stages(stage_id);


--
-- Name: stage_history stage_history_old_stage_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: termosphere
--

ALTER TABLE ONLY public.stage_history
    ADD CONSTRAINT stage_history_old_stage_id_fkey FOREIGN KEY (old_stage_id) REFERENCES public.pipeline_stages(stage_id);


--
-- PostgreSQL database dump complete
--

\unrestrict bpWfaEk3sjRp1fnHJuEvC4oPk319WybFgkvieofPxyEXZyfQMO8T9T1dH9ThrY5

