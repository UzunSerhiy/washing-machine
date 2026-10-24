--
-- PostgreSQL database dump
--

\restrict 7UBUZVzItCPfB65JxNIMDarSkkNsLBbaHJQBeOkaod8XT9lW1g8atOnqgcZDDJi

-- Dumped from database version 17.10 (Debian 17.10-1.pgdg13+1)
-- Dumped by pg_dump version 17.10 (Debian 17.10-1.pgdg13+1)

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
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


ALTER TABLE public.alembic_version OWNER TO postgres;

--
-- Name: drives; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.drives (
    id integer NOT NULL,
    machine_id integer NOT NULL,
    name character varying(100) NOT NULL,
    address integer NOT NULL,
    is_enabled boolean NOT NULL,
    type character varying(20) NOT NULL,
    "position" character varying(20)
);


ALTER TABLE public.drives OWNER TO postgres;

--
-- Name: drives_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.drives_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.drives_id_seq OWNER TO postgres;

--
-- Name: drives_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.drives_id_seq OWNED BY public.drives.id;


--
-- Name: machine_calibrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.machine_calibrations (
    id integer NOT NULL,
    machine_id integer NOT NULL,
    material_start_turns double precision,
    washing_stop_turns double precision,
    water_start_turns double precision
);


ALTER TABLE public.machine_calibrations OWNER TO postgres;

--
-- Name: machine_calibrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.machine_calibrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.machine_calibrations_id_seq OWNER TO postgres;

--
-- Name: machine_calibrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.machine_calibrations_id_seq OWNED BY public.machine_calibrations.id;


--
-- Name: machine_modes; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.machine_modes (
    id integer NOT NULL,
    machine_id integer NOT NULL,
    name character varying(50) NOT NULL,
    code character varying(30) NOT NULL,
    description character varying(500),
    is_enabled boolean NOT NULL
);


ALTER TABLE public.machine_modes OWNER TO postgres;

--
-- Name: machine_modes_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.machine_modes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.machine_modes_id_seq OWNER TO postgres;

--
-- Name: machine_modes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.machine_modes_id_seq OWNED BY public.machine_modes.id;


--
-- Name: machines; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.machines (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    description character varying(500),
    is_active boolean NOT NULL,
    roller_core_diameter_mm double precision NOT NULL
);


ALTER TABLE public.machines OWNER TO postgres;

--
-- Name: machines_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.machines_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.machines_id_seq OWNER TO postgres;

--
-- Name: machines_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.machines_id_seq OWNED BY public.machines.id;


--
-- Name: material_profiles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material_profiles (
    id integer NOT NULL,
    machine_id integer NOT NULL,
    name character varying(100) NOT NULL,
    code character varying(50) NOT NULL,
    description character varying(500),
    is_enabled boolean NOT NULL
);


ALTER TABLE public.material_profiles OWNER TO postgres;

--
-- Name: material_profiles_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.material_profiles_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_profiles_id_seq OWNER TO postgres;

--
-- Name: material_profiles_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_profiles_id_seq OWNED BY public.material_profiles.id;


--
-- Name: mode_speed_settings; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.mode_speed_settings (
    id integer NOT NULL,
    machine_mode_id integer NOT NULL,
    belt_speed_percent double precision NOT NULL,
    material_speed_percent double precision NOT NULL,
    brush_speed_percent double precision
);


ALTER TABLE public.mode_speed_settings OWNER TO postgres;

--
-- Name: mode_speed_settings_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.mode_speed_settings_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.mode_speed_settings_id_seq OWNER TO postgres;

--
-- Name: mode_speed_settings_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.mode_speed_settings_id_seq OWNED BY public.mode_speed_settings.id;


--
-- Name: winding_calibrations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.winding_calibrations (
    id integer NOT NULL,
    material_profile_id integer NOT NULL,
    material_end_turns double precision
);


ALTER TABLE public.winding_calibrations OWNER TO postgres;

--
-- Name: winding_calibrations_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.winding_calibrations_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.winding_calibrations_id_seq OWNER TO postgres;

--
-- Name: winding_calibrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.winding_calibrations_id_seq OWNED BY public.winding_calibrations.id;


--
-- Name: winding_parameters; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.winding_parameters (
    id integer NOT NULL,
    material_profile_id integer NOT NULL,
    core_diameter_mm double precision,
    material_thickness_mm double precision,
    target_speed_m_min double precision,
    calibration_turns double precision,
    calibration_final_diameter_mm double precision
);


ALTER TABLE public.winding_parameters OWNER TO postgres;

--
-- Name: winding_parameters_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.winding_parameters_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.winding_parameters_id_seq OWNER TO postgres;

--
-- Name: winding_parameters_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.winding_parameters_id_seq OWNED BY public.winding_parameters.id;


--
-- Name: drives id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.drives ALTER COLUMN id SET DEFAULT nextval('public.drives_id_seq'::regclass);


--
-- Name: machine_calibrations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_calibrations ALTER COLUMN id SET DEFAULT nextval('public.machine_calibrations_id_seq'::regclass);


--
-- Name: machine_modes id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_modes ALTER COLUMN id SET DEFAULT nextval('public.machine_modes_id_seq'::regclass);


--
-- Name: machines id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines ALTER COLUMN id SET DEFAULT nextval('public.machines_id_seq'::regclass);


--
-- Name: material_profiles id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_profiles ALTER COLUMN id SET DEFAULT nextval('public.material_profiles_id_seq'::regclass);


--
-- Name: mode_speed_settings id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mode_speed_settings ALTER COLUMN id SET DEFAULT nextval('public.mode_speed_settings_id_seq'::regclass);


--
-- Name: winding_calibrations id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_calibrations ALTER COLUMN id SET DEFAULT nextval('public.winding_calibrations_id_seq'::regclass);


--
-- Name: winding_parameters id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_parameters ALTER COLUMN id SET DEFAULT nextval('public.winding_parameters_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.alembic_version (version_num) FROM stdin;
a83f1b09d627
\.


--
-- Data for Name: drives; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.drives (id, machine_id, name, address, is_enabled, type, "position") FROM stdin;
1	1	Brush Left	3	t	BRUSH	LEFT
2	1	Brush Right	2	t	BRUSH	RIGHT
3	1	Roller	1	t	ROLLER	\N
\.


--
-- Data for Name: machine_calibrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.machine_calibrations (id, machine_id, material_start_turns, washing_stop_turns, water_start_turns) FROM stdin;
\.


--
-- Data for Name: machine_modes; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.machine_modes (id, machine_id, name, code, description, is_enabled) FROM stdin;
1	1	Намотка	WINDING	Наматывание материала	t
2	1	Мойка	WASHING	Основной режим мойки	t
3	1	Сушка	DRYING	Режим сушки материала	t
4	1	Размотка	UNWINDING	Разматывание материала	t
\.


--
-- Data for Name: machines; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.machines (id, name, description, is_active, roller_core_diameter_mm) FROM stdin;
1	Washing Machine	Industrial washing machine	t	200
\.


--
-- Data for Name: material_profiles; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material_profiles (id, machine_id, name, code, description, is_enabled) FROM stdin;
1	1	Дах 5м	ROOF_5M	Дахове покриття 5 м	t
2	1	Дах 10м	ROOF_10M	Дахове покриття 10 м	t
3	1	Дах 15м	ROOF_15M	Дахoве покриття 15 м	t
4	1	Дах 20м	ROOF_20M	Дахoве покриття 20 м	t
5	1	Дах 30м	ROOF_30M	Дахoве покриття 30 м	t
6	1	Дах 40M	ROOF_40M	Дахoве покриття 40 м	t
7	1	Дах 50м	ROOF_50M	Дахoве покриття 50 м	t
8	1	Стіна 2.3 м	WALL_2_3M	Висота стіни 2.3 м	t
9	1	Стіна 3 м	WALL_3M	Висота стіни 3 м	t
10	1	Стіна 4 м	WALL_4M	Висота стіни 4 м	t
11	1	Трикутник 5 м	TRIANGLE_5M	Трикутник довжиною 5 м (10)	t
12	1	Трикутник 7.5 м	TRIANGLE_7_5M	Трикутник довжиною 7.5 м (15)	t
13	1	Трикутник 10 м	TRIANGLE_10M	Ткрикутник довжиною 10 м (20)	t
14	1	Трикутник 15 м	TRIANGLE_15M	Ткрикутник довжиною 15 м (30)	t
15	1	Трикутник 20 м	TRIANGLE_20M	Ткрикутник довжиною 20 м (40)	t
16	1	Трикутник 25 м	TRIANGLE_25M	Ткрикутник довжиною 25 м (50)	t
\.


--
-- Data for Name: mode_speed_settings; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.mode_speed_settings (id, machine_mode_id, belt_speed_percent, material_speed_percent, brush_speed_percent) FROM stdin;
1	1	70	70	\N
2	2	60	60	90
3	3	30	30	30
4	4	80	80	\N
\.


--
-- Data for Name: winding_calibrations; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.winding_calibrations (id, material_profile_id, material_end_turns) FROM stdin;
\.


--
-- Data for Name: winding_parameters; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.winding_parameters (id, material_profile_id, core_diameter_mm, material_thickness_mm, target_speed_m_min, calibration_turns, calibration_final_diameter_mm) FROM stdin;
\.


--
-- Name: drives_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.drives_id_seq', 3, true);


--
-- Name: machine_calibrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.machine_calibrations_id_seq', 1, false);


--
-- Name: machine_modes_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.machine_modes_id_seq', 4, true);


--
-- Name: machines_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.machines_id_seq', 1, true);


--
-- Name: material_profiles_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_profiles_id_seq', 16, true);


--
-- Name: mode_speed_settings_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.mode_speed_settings_id_seq', 4, true);


--
-- Name: winding_calibrations_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.winding_calibrations_id_seq', 1, false);


--
-- Name: winding_parameters_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.winding_parameters_id_seq', 1, false);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: drives drives_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.drives
    ADD CONSTRAINT drives_pkey PRIMARY KEY (id);


--
-- Name: machine_calibrations machine_calibrations_machine_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_calibrations
    ADD CONSTRAINT machine_calibrations_machine_id_key UNIQUE (machine_id);


--
-- Name: machine_calibrations machine_calibrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_calibrations
    ADD CONSTRAINT machine_calibrations_pkey PRIMARY KEY (id);


--
-- Name: machine_modes machine_modes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_modes
    ADD CONSTRAINT machine_modes_pkey PRIMARY KEY (id);


--
-- Name: machines machines_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machines
    ADD CONSTRAINT machines_pkey PRIMARY KEY (id);


--
-- Name: material_profiles material_profiles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_profiles
    ADD CONSTRAINT material_profiles_pkey PRIMARY KEY (id);


--
-- Name: mode_speed_settings mode_speed_settings_machine_mode_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mode_speed_settings
    ADD CONSTRAINT mode_speed_settings_machine_mode_id_key UNIQUE (machine_mode_id);


--
-- Name: mode_speed_settings mode_speed_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mode_speed_settings
    ADD CONSTRAINT mode_speed_settings_pkey PRIMARY KEY (id);


--
-- Name: winding_calibrations uq_winding_calibrations_material_profile_id; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_calibrations
    ADD CONSTRAINT uq_winding_calibrations_material_profile_id UNIQUE (material_profile_id);


--
-- Name: winding_calibrations winding_calibrations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_calibrations
    ADD CONSTRAINT winding_calibrations_pkey PRIMARY KEY (id);


--
-- Name: winding_parameters winding_parameters_material_profile_id_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_parameters
    ADD CONSTRAINT winding_parameters_material_profile_id_key UNIQUE (material_profile_id);


--
-- Name: winding_parameters winding_parameters_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_parameters
    ADD CONSTRAINT winding_parameters_pkey PRIMARY KEY (id);


--
-- Name: drives drives_machine_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.drives
    ADD CONSTRAINT drives_machine_id_fkey FOREIGN KEY (machine_id) REFERENCES public.machines(id);


--
-- Name: machine_calibrations machine_calibrations_machine_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_calibrations
    ADD CONSTRAINT machine_calibrations_machine_id_fkey FOREIGN KEY (machine_id) REFERENCES public.machines(id);


--
-- Name: machine_modes machine_modes_machine_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.machine_modes
    ADD CONSTRAINT machine_modes_machine_id_fkey FOREIGN KEY (machine_id) REFERENCES public.machines(id);


--
-- Name: material_profiles material_profiles_machine_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material_profiles
    ADD CONSTRAINT material_profiles_machine_id_fkey FOREIGN KEY (machine_id) REFERENCES public.machines(id);


--
-- Name: mode_speed_settings mode_speed_settings_machine_mode_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.mode_speed_settings
    ADD CONSTRAINT mode_speed_settings_machine_mode_id_fkey FOREIGN KEY (machine_mode_id) REFERENCES public.machine_modes(id);


--
-- Name: winding_calibrations winding_calibrations_material_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_calibrations
    ADD CONSTRAINT winding_calibrations_material_profile_id_fkey FOREIGN KEY (material_profile_id) REFERENCES public.material_profiles(id);


--
-- Name: winding_parameters winding_parameters_material_profile_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.winding_parameters
    ADD CONSTRAINT winding_parameters_material_profile_id_fkey FOREIGN KEY (material_profile_id) REFERENCES public.material_profiles(id);


--
-- PostgreSQL database dump complete
--

\unrestrict 7UBUZVzItCPfB65JxNIMDarSkkNsLBbaHJQBeOkaod8XT9lW1g8atOnqgcZDDJi

