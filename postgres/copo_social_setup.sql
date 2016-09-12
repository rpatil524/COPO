--
-- PostgreSQL database dump
--

-- Dumped from database version 9.5.1
-- Dumped by pg_dump version 9.5.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;

SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: django_site; Type: TABLE; Schema: public; Owner: copo_user
--

CREATE TABLE django_site (
    id integer NOT NULL,
    domain character varying(100) NOT NULL,
    name character varying(50) NOT NULL
);


ALTER TABLE django_site OWNER TO copo_user;

--
-- Name: django_site_id_seq; Type: SEQUENCE; Schema: public; Owner: copo_user
--

CREATE SEQUENCE django_site_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE django_site_id_seq OWNER TO copo_user;

--
-- Name: django_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: copo_user
--

ALTER SEQUENCE django_site_id_seq OWNED BY django_site.id;


--
-- Name: socialaccount_socialapp; Type: TABLE; Schema: public; Owner: copo_user
--

CREATE TABLE socialaccount_socialapp (
    id integer NOT NULL,
    provider character varying(30) NOT NULL,
    name character varying(40) NOT NULL,
    client_id character varying(100) NOT NULL,
    secret character varying(100) NOT NULL,
    key character varying(100) NOT NULL
);


ALTER TABLE socialaccount_socialapp OWNER TO copo_user;

--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE; Schema: public; Owner: copo_user
--

CREATE SEQUENCE socialaccount_socialapp_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE socialaccount_socialapp_id_seq OWNER TO copo_user;

--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: copo_user
--

ALTER SEQUENCE socialaccount_socialapp_id_seq OWNED BY socialaccount_socialapp.id;


--
-- Name: socialaccount_socialapp_sites; Type: TABLE; Schema: public; Owner: copo_user
--

CREATE TABLE socialaccount_socialapp_sites (
    id integer NOT NULL,
    socialapp_id integer NOT NULL,
    site_id integer NOT NULL
);


ALTER TABLE socialaccount_socialapp_sites OWNER TO copo_user;

--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE; Schema: public; Owner: copo_user
--

CREATE SEQUENCE socialaccount_socialapp_sites_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE socialaccount_socialapp_sites_id_seq OWNER TO copo_user;

--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: copo_user
--

ALTER SEQUENCE socialaccount_socialapp_sites_id_seq OWNED BY socialaccount_socialapp_sites.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY django_site ALTER COLUMN id SET DEFAULT nextval('django_site_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp ALTER COLUMN id SET DEFAULT nextval('socialaccount_socialapp_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp_sites ALTER COLUMN id SET DEFAULT nextval('socialaccount_socialapp_sites_id_seq'::regclass);


--
-- Data for Name: django_site; Type: TABLE DATA; Schema: public; Owner: copo_user
--

COPY django_site (id, domain, name) FROM stdin;
3	www.copo-project.org	www.copo-project.org
\.


--
-- Name: django_site_id_seq; Type: SEQUENCE SET; Schema: public; Owner: copo_user
--

SELECT pg_catalog.setval('django_site_id_seq', 3, true);


--
-- Data for Name: socialaccount_socialapp; Type: TABLE DATA; Schema: public; Owner: copo_user
--

COPY socialaccount_socialapp (id, provider, name, client_id, secret, key) FROM stdin;
1	google	Google	197718904608-mubhgir39dr8e159ef4hb3l5i8me71b6.apps.googleusercontent.com	-17-37tDbzaqg52uM25r_6W8	
2	orcid	Orcid	APP-EGMH46B26C2OCJ9F	9acf1932-ca1c-4892-9217-72e11bd7d4a5	
\.


--
-- Name: socialaccount_socialapp_id_seq; Type: SEQUENCE SET; Schema: public; Owner: copo_user
--

SELECT pg_catalog.setval('socialaccount_socialapp_id_seq', 1, false);


--
-- Data for Name: socialaccount_socialapp_sites; Type: TABLE DATA; Schema: public; Owner: copo_user
--

COPY socialaccount_socialapp_sites (id, socialapp_id, site_id) FROM stdin;
1	1	3
2	2	3
\.


--
-- Name: socialaccount_socialapp_sites_id_seq; Type: SEQUENCE SET; Schema: public; Owner: copo_user
--

SELECT pg_catalog.setval('socialaccount_socialapp_sites_id_seq', 1, false);


--
-- Name: django_site_pkey; Type: CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY django_site
    ADD CONSTRAINT django_site_pkey PRIMARY KEY (id);


--
-- Name: socialaccount_socialapp_pkey; Type: CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp
    ADD CONSTRAINT socialaccount_socialapp_pkey PRIMARY KEY (id);


--
-- Name: socialaccount_socialapp_sites_pkey; Type: CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp_sites
    ADD CONSTRAINT socialaccount_socialapp_sites_pkey PRIMARY KEY (id);


--
-- Name: socialaccount_socialapp_sites_socialapp_id_site_id_key; Type: CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp_sites
    ADD CONSTRAINT socialaccount_socialapp_sites_socialapp_id_site_id_key UNIQUE (socialapp_id, site_id);


--
-- Name: socialaccount_socialapp_sites_9365d6e7; Type: INDEX; Schema: public; Owner: copo_user
--

CREATE INDEX socialaccount_socialapp_sites_9365d6e7 ON socialaccount_socialapp_sites USING btree (site_id);


--
-- Name: socialaccount_socialapp_sites_fe95b0a0; Type: INDEX; Schema: public; Owner: copo_user
--

CREATE INDEX socialaccount_socialapp_sites_fe95b0a0 ON socialaccount_socialapp_sites USING btree (socialapp_id);


--
-- Name: soc_socialapp_id_24aa4c792c2bb11d_fk_socialaccount_socialapp_id; Type: FK CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp_sites
    ADD CONSTRAINT soc_socialapp_id_24aa4c792c2bb11d_fk_socialaccount_socialapp_id FOREIGN KEY (socialapp_id) REFERENCES socialaccount_socialapp(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: socialaccount_social_site_id_353177fe56af6e3c_fk_django_site_id; Type: FK CONSTRAINT; Schema: public; Owner: copo_user
--

ALTER TABLE ONLY socialaccount_socialapp_sites
    ADD CONSTRAINT socialaccount_social_site_id_353177fe56af6e3c_fk_django_site_id FOREIGN KEY (site_id) REFERENCES django_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- PostgreSQL database dump complete
--

