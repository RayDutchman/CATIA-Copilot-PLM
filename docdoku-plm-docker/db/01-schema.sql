--
-- PostgreSQL database dump
--

-- Dumped from database version 13.1
-- Dumped by pg_dump version 13.1

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
-- Name: account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.account (
    login character varying(255) NOT NULL,
    creationdate timestamp without time zone,
    email character varying(255),
    enabled boolean,
    language character varying(255),
    name character varying(255),
    timezone character varying(255)
);


--
-- Name: acl; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acl (
    id integer NOT NULL,
    enabled boolean
);


--
-- Name: acl_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.acl_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: acl_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.acl_id_seq OWNED BY public.acl.id;


--
-- Name: acluserentry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.acluserentry (
    permission integer,
    acl_id integer NOT NULL,
    principal_login character varying(255) NOT NULL,
    principal_workspace_id character varying(100) NOT NULL
);


--
-- Name: aclusergroupentry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aclusergroupentry (
    permission integer,
    acl_id integer NOT NULL,
    principal_workspace_id character varying(100) NOT NULL,
    principal_id character varying(100) NOT NULL
);


--
-- Name: activity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity (
    step integer NOT NULL,
    dtype character varying(31),
    lifecyclestate character varying(255),
    workflow_id integer NOT NULL,
    taskstocomplete integer
);


--
-- Name: activity_relaunch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activity_relaunch (
    activity_step integer NOT NULL,
    activity_workflow_id integer NOT NULL,
    relaunch_step integer NOT NULL,
    relaunch_workflow_id integer NOT NULL
);


--
-- Name: activitymodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activitymodel (
    id integer NOT NULL,
    dtype character varying(31),
    lifecyclestate character varying(255),
    step integer,
    workspace_id character varying(100),
    workflowmodel_id character varying(100),
    taskstocomplete integer
);


--
-- Name: activitymodel_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.activitymodel_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: activitymodel_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.activitymodel_id_seq OWNED BY public.activitymodel.id;


--
-- Name: activitymodel_relaunch; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.activitymodel_relaunch (
    activitymodel_id integer NOT NULL,
    relaunchactivitymodel_id integer NOT NULL
);


--
-- Name: attribute_namevalue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attribute_namevalue (
    name character varying(255),
    value character varying(255),
    attribute_id integer,
    namevalue_order integer
);


--
-- Name: baselineddocument; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.baselineddocument (
    target_iteration integer NOT NULL,
    documentcollection_id integer NOT NULL,
    target_documentmaster_id character varying(100) NOT NULL,
    target_docrevision_version character varying(10) NOT NULL,
    target_workspace_id character varying(100) NOT NULL
);


--
-- Name: baselinedpart; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.baselinedpart (
    target_iteration integer NOT NULL,
    target_partrevision_version character varying(10) NOT NULL,
    partcollection_id integer NOT NULL,
    target_partmaster_partnumber character varying(100) NOT NULL,
    target_workspace_id character varying(100) NOT NULL
);


--
-- Name: binaryresource; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.binaryresource (
    fullname character varying(722) NOT NULL,
    dtype character varying(31),
    contentlength bigint,
    lastmodified timestamp without time zone,
    quality integer,
    x_max double precision,
    x_min double precision,
    y_max double precision,
    y_min double precision,
    z_max double precision,
    z_min double precision
);


--
-- Name: cadinstance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cadinstance (
    id integer NOT NULL,
    rotationtype character varying(255),
    rx double precision,
    ry double precision,
    rz double precision,
    tx double precision,
    ty double precision,
    tz double precision,
    m00 double precision,
    m01 double precision,
    m02 double precision,
    m10 double precision,
    m11 double precision,
    m12 double precision,
    m20 double precision,
    m21 double precision,
    m22 double precision
);


--
-- Name: cadinstance_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cadinstance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cadinstance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cadinstance_id_seq OWNED BY public.cadinstance.id;


--
-- Name: changeissue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeissue (
    id integer NOT NULL,
    category integer,
    creationdate timestamp without time zone,
    description text,
    initiator character varying(255),
    name character varying(255),
    priority integer,
    assignee_workspace_id character varying(100),
    assignee_login character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100),
    acl_id integer
);


--
-- Name: changeissue_affected_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeissue_affected_document (
    changeissue_id integer NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changeissue_affected_part; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeissue_affected_part (
    changeissue_id integer NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    partmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changeissue_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.changeissue_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: changeissue_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.changeissue_id_seq OWNED BY public.changeissue.id;


--
-- Name: changeissue_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeissue_tag (
    changeissue_id integer NOT NULL,
    tag_label character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL
);


--
-- Name: changeorder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeorder (
    id integer NOT NULL,
    category integer,
    creationdate timestamp without time zone,
    description text,
    name character varying(255),
    priority integer,
    assignee_workspace_id character varying(100),
    assignee_login character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    milestone_id integer,
    workspace_id character varying(100),
    acl_id integer
);


--
-- Name: changeorder_affected_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeorder_affected_document (
    changeorder_id integer NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changeorder_affected_part; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeorder_affected_part (
    changeorder_id integer NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    partmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changeorder_changerequest; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeorder_changerequest (
    changeorder_id integer NOT NULL,
    changerequest_id integer NOT NULL
);


--
-- Name: changeorder_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.changeorder_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: changeorder_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.changeorder_id_seq OWNED BY public.changeorder.id;


--
-- Name: changeorder_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changeorder_tag (
    changeorder_id integer NOT NULL,
    tag_label character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL
);


--
-- Name: changereq_affected_document; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changereq_affected_document (
    changerequest_id integer NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changereq_affected_part; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changereq_affected_part (
    changerequest_id integer NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    partmaster_workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL
);


--
-- Name: changerequest; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changerequest (
    id integer NOT NULL,
    category integer,
    creationdate timestamp without time zone,
    description text,
    name character varying(255),
    priority integer,
    assignee_workspace_id character varying(100),
    assignee_login character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    milestone_id integer,
    workspace_id character varying(100),
    acl_id integer
);


--
-- Name: changerequest_changeissue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changerequest_changeissue (
    changerequest_id integer NOT NULL,
    changeissue_id integer NOT NULL
);


--
-- Name: changerequest_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.changerequest_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: changerequest_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.changerequest_id_seq OWNED BY public.changerequest.id;


--
-- Name: changerequest_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.changerequest_tag (
    changerequest_id integer NOT NULL,
    tag_label character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL
);


--
-- Name: configurationitem; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationitem (
    id character varying(100) NOT NULL,
    description text,
    author_workspace_id character varying(100),
    author_login character varying(255),
    partmaster_workspace_id character varying(100),
    partmaster_partnumber character varying(100),
    workspace_id character varying(100) NOT NULL
);


--
-- Name: configurationitem_p2plink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configurationitem_p2plink (
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    pathtopathlink_id integer NOT NULL
);


--
-- Name: conversion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversion (
    enddate timestamp without time zone,
    pending boolean,
    startdate timestamp without time zone,
    succeed boolean,
    workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL
);


--
-- Name: credential; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credential (
    login character varying(255) NOT NULL,
    password character varying(255)
);


--
-- Name: document_aborted_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_aborted_workflow (
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    workflow_id integer NOT NULL
);


--
-- Name: documentbaseline; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentbaseline (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    description text,
    name character varying(255) NOT NULL,
    type integer,
    author_workspace_id character varying(100),
    author_login character varying(255),
    documentcollection_id integer
);


--
-- Name: documentbaseline_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentbaseline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentbaseline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentbaseline_id_seq OWNED BY public.documentbaseline.id;


--
-- Name: documentcollection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentcollection (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    author_workspace_id character varying(100),
    author_login character varying(255)
);


--
-- Name: documentcollection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentcollection_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentcollection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentcollection_id_seq OWNED BY public.documentcollection.id;


--
-- Name: documentiteration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentiteration (
    iteration integer NOT NULL,
    checkindate timestamp without time zone,
    creationdate timestamp without time zone,
    modificationdate timestamp without time zone,
    revisionnote character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_id character varying(100) NOT NULL
);


--
-- Name: documentiteration_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentiteration_attribute (
    workspace_id character varying(100) NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    instanceattribute_id integer NOT NULL,
    attribute_order integer
);


--
-- Name: documentiteration_binres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentiteration_binres (
    workspace_id character varying(100) NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    attachedfile_fullname character varying(722) NOT NULL
);


--
-- Name: documentiteration_documentlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentiteration_documentlink (
    workspace_id character varying(100) NOT NULL,
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    documentlink_id integer NOT NULL
);


--
-- Name: documentlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentlink (
    id integer NOT NULL,
    commentdata character varying(255),
    target_documentmaster_id character varying(100),
    target_docrevision_version character varying(10),
    target_workspace_id character varying(100)
);


--
-- Name: documentlink_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentlink_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentlink_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentlink_id_seq OWNED BY public.documentlink.id;


--
-- Name: documentlog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentlog (
    id integer NOT NULL,
    documentid character varying(255),
    documentiteration integer,
    documentversion character varying(255),
    documentworkspaceid character varying(255),
    event character varying(255),
    info character varying(255),
    logdate timestamp without time zone,
    userlogin character varying(255)
);


--
-- Name: documentlog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documentlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documentlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documentlog_id_seq OWNED BY public.documentlog.id;


--
-- Name: documentmaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentmaster (
    id character varying(100) NOT NULL,
    attributeslocked boolean,
    creationdate timestamp without time zone,
    type character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100) NOT NULL
);


--
-- Name: documentmastertemplate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentmastertemplate (
    id character varying(100) NOT NULL,
    attributeslocked boolean,
    creationdate timestamp without time zone,
    documenttype character varying(255),
    idgenerated boolean,
    mask character varying(255),
    modificationdate timestamp without time zone,
    workflowmodel_id character varying(100),
    workspace_id character varying(100) NOT NULL,
    author_workspace_id character varying(100),
    author_login character varying(255),
    workflowmodel_workspace_id character varying(100),
    acl_id integer
);


--
-- Name: documentmastertemplate_attr; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentmastertemplate_attr (
    workspace_id character varying(100) NOT NULL,
    documentmastertemplate_id character varying(100) NOT NULL,
    instanceattributetemplate_id integer NOT NULL,
    attr_order integer
);


--
-- Name: documentmastertemplate_binres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentmastertemplate_binres (
    workspace_id character varying(100) NOT NULL,
    documentmastertemplate_id character varying(100) NOT NULL,
    attachedfile_fullname character varying(722) NOT NULL
);


--
-- Name: documentrevision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentrevision (
    version character varying(10) NOT NULL,
    checkoutdate timestamp without time zone,
    creationdate timestamp without time zone,
    description text,
    documentmaster_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    publicshared boolean,
    status integer,
    title character varying(255),
    obsolete_date timestamp without time zone,
    obsolete_user_workspace character varying(100),
    obsolete_user_login character varying(255),
    release_date timestamp without time zone,
    release_user_workspace character varying(100),
    release_user_login character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    checkoutuser_workspace_id character varying(100),
    checkoutuser_login character varying(255),
    location_completepath character varying(1024),
    acl_id integer,
    workflow_id integer
);


--
-- Name: documentrevision_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documentrevision_tag (
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    tag_label character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL
);


--
-- Name: effectivity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.effectivity (
    id integer NOT NULL,
    dtype character varying(31),
    description text,
    name character varying(255),
    configurationitem_id character varying(100),
    configurationitem_workspace_id character varying(100),
    enddate timestamp without time zone,
    startdate timestamp without time zone,
    endlotid character varying(255),
    startlotid character varying(255),
    endnumber character varying(255),
    startnumber character varying(255)
);


--
-- Name: effectivity_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.effectivity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: effectivity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.effectivity_id_seq OWNED BY public.effectivity.id;


--
-- Name: folder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.folder (
    completepath character varying(1024) NOT NULL,
    parentfolder_completepath character varying(1024)
);


--
-- Name: gcmaccount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.gcmaccount (
    gcmid character varying(255),
    account_login character varying(255) NOT NULL
);


--
-- Name: import; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import (
    id character varying(255) NOT NULL,
    enddate timestamp without time zone,
    filename character varying(255),
    pending boolean,
    startdate timestamp without time zone,
    succeed boolean,
    user_login character varying(255),
    user_workspace_id character varying(100)
);


--
-- Name: import_error; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_error (
    import_id character varying(255),
    errors character varying(255)
);


--
-- Name: import_warning; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.import_warning (
    import_id character varying(255),
    warnings character varying(255)
);


--
-- Name: instanceattribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instanceattribute (
    id integer NOT NULL,
    dtype character varying(31),
    locked boolean,
    mandatory boolean,
    name character varying(255),
    booleanvalue boolean,
    datevalue timestamp without time zone,
    indexvalue integer,
    numbervalue double precision,
    textvalue character varying(255),
    longtextvalue text,
    urlvalue character varying(255),
    partmaster_workspace_id character varying(100),
    partmaster_partnumber character varying(100)
);


--
-- Name: instanceattribute_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instanceattribute_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instanceattribute_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instanceattribute_id_seq OWNED BY public.instanceattribute.id;


--
-- Name: instanceattributetemplate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instanceattributetemplate (
    id integer NOT NULL,
    dtype character varying(31),
    locked boolean,
    mandatory boolean,
    name character varying(100),
    attributetype integer,
    lov_name character varying(100),
    lov_workspace_id character varying(100)
);


--
-- Name: instanceattributetemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instanceattributetemplate_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instanceattributetemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instanceattributetemplate_id_seq OWNED BY public.instanceattributetemplate.id;


--
-- Name: iterationchangesubscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.iterationchangesubscription (
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    subscriber_login character varying(255) NOT NULL,
    subscriber_workspace_id character varying(100) NOT NULL
);


--
-- Name: layer; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer (
    id integer NOT NULL,
    color character varying(255),
    creationdate timestamp without time zone,
    name character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    configurationitem_id character varying(100),
    configurationitem_workspace_id character varying(100)
);


--
-- Name: layer_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.layer_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: layer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.layer_id_seq OWNED BY public.layer.id;


--
-- Name: layer_marker; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.layer_marker (
    layer_id integer NOT NULL,
    marker_id integer NOT NULL
);


--
-- Name: lov; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lov (
    name character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: lov_namevalue; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lov_namevalue (
    name character varying(255),
    value character varying(255),
    lov_name character varying(100),
    lov_workspace_id character varying(100),
    namevalue_order integer
);


--
-- Name: marker; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marker (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    description text,
    title character varying(255),
    x double precision,
    y double precision,
    z double precision,
    author_workspace_id character varying(100),
    author_login character varying(255)
);


--
-- Name: marker_effectivity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marker_effectivity (
    marker_id integer NOT NULL,
    effectivity_id integer NOT NULL
);


--
-- Name: marker_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.marker_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: marker_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.marker_id_seq OWNED BY public.marker.id;


--
-- Name: marker_partmaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.marker_partmaster (
    marker_id integer NOT NULL,
    relatedpart_workspace_id character varying(100) NOT NULL,
    relatedpart_partnumber character varying(100) NOT NULL
);


--
-- Name: milestone; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.milestone (
    id integer NOT NULL,
    description text,
    duedate timestamp without time zone,
    title character varying(255),
    workspace_id character varying(100),
    acl_id integer
);


--
-- Name: milestone_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.milestone_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: milestone_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.milestone_id_seq OWNED BY public.milestone.id;


--
-- Name: modificationnotification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modificationnotification (
    id integer NOT NULL,
    acknowledged boolean,
    acknowledgementcomment text,
    acknowledgementdate timestamp without time zone,
    ackauthor_workspace_id character varying(100),
    ackauthor_login character varying(255),
    impacted_partrevision_version character varying(10),
    impacted_iteration integer,
    impacted_workspace_id character varying(100),
    impacted_partmaster_partnumber character varying(100),
    modified_workspace_id character varying(100),
    modified_partmaster_partnumber character varying(100),
    modified_iteration integer,
    modified_partrevision_version character varying(10)
);


--
-- Name: modificationnotification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.modificationnotification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: modificationnotification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.modificationnotification_id_seq OWNED BY public.modificationnotification.id;


--
-- Name: oauthprovider; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.oauthprovider (
    id integer NOT NULL,
    authority character varying(255),
    authorizationendpoint character varying(255),
    clientid character varying(255),
    enabled boolean,
    issuer character varying(255),
    jwkseturl character varying(255),
    jwsalgorithm character varying(255),
    name character varying(255),
    redirecturi character varying(255),
    responsetype character varying(255),
    scope character varying(255),
    secret character varying(255)
);


--
-- Name: oauthprovider_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.oauthprovider_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: oauthprovider_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.oauthprovider_id_seq OWNED BY public.oauthprovider.id;


--
-- Name: organization; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization (
    name character varying(100) NOT NULL,
    description text,
    owner_login character varying(255)
);


--
-- Name: organization_account; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_account (
    organization_name character varying(100) NOT NULL,
    account_login character varying(255) NOT NULL,
    account_order integer
);


--
-- Name: part_aborted_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.part_aborted_workflow (
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    partmaster_workspace_id character varying(100) NOT NULL,
    workflow_id integer NOT NULL
);


--
-- Name: partcollection; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partcollection (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    author_workspace_id character varying(100),
    author_login character varying(255)
);


--
-- Name: partcollection_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.partcollection_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: partcollection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.partcollection_id_seq OWNED BY public.partcollection.id;


--
-- Name: partiteration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration (
    iteration integer NOT NULL,
    checkindate timestamp without time zone,
    creationdate timestamp without time zone,
    iterationnote character varying(255),
    modificationdate timestamp without time zone,
    source integer,
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    nativecadfile_fullname character varying(722)
);


--
-- Name: partiteration_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_attribute (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    instanceattribute_id integer NOT NULL,
    attribute_order integer
);


--
-- Name: partiteration_binres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_binres (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    attachedfile_fullname character varying(722) NOT NULL
);


--
-- Name: partiteration_documentlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_documentlink (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    documentlink_id integer NOT NULL
);


--
-- Name: partiteration_geometry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_geometry (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    geometry_fullname character varying(722) NOT NULL
);


--
-- Name: partiteration_partusagelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_partusagelink (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    component_id integer NOT NULL,
    component_order integer
);


--
-- Name: partiteration_pathdata_attr; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partiteration_pathdata_attr (
    workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    iteration integer NOT NULL,
    instanceattribute_template_id integer NOT NULL,
    attribute_order integer
);


--
-- Name: partlog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partlog (
    id integer NOT NULL,
    event character varying(255),
    info character varying(255),
    logdate timestamp without time zone,
    partiteration integer,
    partnumber character varying(255),
    partversion character varying(255),
    partworkspaceid character varying(255),
    userlogin character varying(255)
);


--
-- Name: partlog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.partlog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: partlog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.partlog_id_seq OWNED BY public.partlog.id;


--
-- Name: partmaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partmaster (
    partnumber character varying(100) NOT NULL,
    attributeslocked boolean,
    creationdate timestamp without time zone,
    name character varying(255),
    standardpart boolean,
    type character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100) NOT NULL
);


--
-- Name: partmaster_alternate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partmaster_alternate (
    commentdata character varying(255),
    referencedescription character varying(255),
    alternate_partnumber character varying(100),
    alternate_workspace_id character varying(100),
    partmaster_workspace_id character varying(100),
    partmaster_partnumber character varying(100),
    alternate_order integer
);


--
-- Name: partmastertemplate; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partmastertemplate (
    id character varying(100) NOT NULL,
    attributeslocked boolean,
    creationdate timestamp without time zone,
    idgenerated boolean,
    mask character varying(255),
    modificationdate timestamp without time zone,
    parttype character varying(255),
    workflowmodel_id character varying(100),
    workspace_id character varying(100) NOT NULL,
    author_workspace_id character varying(100),
    author_login character varying(255),
    workflowmodel_workspace_id character varying(100),
    acl_id integer,
    attachedfile_fullname character varying(722)
);


--
-- Name: partmastertemplate_attr; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partmastertemplate_attr (
    workspace_id character varying(100) NOT NULL,
    partmastertemplate_id character varying(100) NOT NULL,
    instanceattributetemplate_id integer NOT NULL,
    attr_order integer
);


--
-- Name: partmastertpl_instance_attr; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partmastertpl_instance_attr (
    workspace_id character varying(100) NOT NULL,
    partmastertemplate_id character varying(100) NOT NULL,
    instanceattributetemplate_id integer NOT NULL,
    attr_order integer
);


--
-- Name: partrevision; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partrevision (
    version character varying(10) NOT NULL,
    checkoutdate timestamp without time zone,
    creationdate timestamp without time zone,
    description text,
    partmaster_partnumber character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    publicshared boolean,
    status integer,
    obsolete_date timestamp without time zone,
    obsolete_user_workspace character varying(100),
    obsolete_user_login character varying(255),
    release_date timestamp without time zone,
    release_user_workspace character varying(100),
    release_user_login character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    checkoutuser_workspace_id character varying(100),
    checkoutuser_login character varying(255),
    acl_id integer,
    workflow_id integer
);


--
-- Name: partrevision_effectivity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partrevision_effectivity (
    partmaster_workspace_id character varying(100) NOT NULL,
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    effectivity_id integer NOT NULL
);


--
-- Name: partrevision_tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partrevision_tag (
    partmaster_partnumber character varying(100) NOT NULL,
    partrevision_version character varying(10) NOT NULL,
    partmaster_workspace_id character varying(100) NOT NULL,
    tag_label character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL
);


--
-- Name: partsubstitutelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partsubstitutelink (
    id integer NOT NULL,
    amount double precision,
    commentdata character varying(255),
    referencedescription character varying(255),
    unit character varying(255),
    substitute_workspace_id character varying(100),
    substitute_partnumber character varying(100)
);


--
-- Name: partsubstitutelink_cadinstance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partsubstitutelink_cadinstance (
    partsubstitutelink_id integer NOT NULL,
    cadinstance_id integer NOT NULL,
    cadinstance_order integer
);


--
-- Name: partsubstitutelink_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.partsubstitutelink_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: partsubstitutelink_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.partsubstitutelink_id_seq OWNED BY public.partsubstitutelink.id;


--
-- Name: partusagelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partusagelink (
    id integer NOT NULL,
    amount double precision,
    commentdata character varying(255),
    optional boolean,
    referencedescription character varying(255),
    unit character varying(255),
    component_partnumber character varying(100),
    component_workspace_id character varying(100)
);


--
-- Name: partusagelink_cadinstance; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partusagelink_cadinstance (
    partusagelink_id integer NOT NULL,
    cadinstance_id integer NOT NULL,
    cadinstance_order integer
);


--
-- Name: partusagelink_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.partusagelink_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: partusagelink_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.partusagelink_id_seq OWNED BY public.partusagelink.id;


--
-- Name: passwordrecoveryrequest; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.passwordrecoveryrequest (
    uuid character varying(255) NOT NULL,
    login character varying(255)
);


--
-- Name: pathdataiteration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathdataiteration (
    iteration integer NOT NULL,
    dateiteration timestamp without time zone,
    iterationnote text,
    pathdatamaster_id integer NOT NULL
);


--
-- Name: pathdataiteration_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathdataiteration_attribute (
    pathdata_iteration integer NOT NULL,
    pathdatamaster_id integer NOT NULL,
    instanceattribute_id integer NOT NULL,
    attribute_order integer
);


--
-- Name: pathdataiteration_binres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathdataiteration_binres (
    pathdata_iteration integer NOT NULL,
    pathdatamaster_id integer NOT NULL,
    attachedfile_fullname character varying(722) NOT NULL
);


--
-- Name: pathdataiteration_documentlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathdataiteration_documentlink (
    pathdata_iteration integer NOT NULL,
    pathdatamaster_id integer NOT NULL,
    documentlink_id integer NOT NULL
);


--
-- Name: pathdatamaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathdatamaster (
    id integer NOT NULL,
    path character varying(255)
);


--
-- Name: pathdatamaster_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pathdatamaster_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pathdatamaster_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pathdatamaster_id_seq OWNED BY public.pathdatamaster.id;


--
-- Name: pathtopathlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pathtopathlink (
    id integer NOT NULL,
    description text,
    sourcepath character varying(255),
    targetpath character varying(255),
    type character varying(255)
);


--
-- Name: pathtopathlink_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.pathtopathlink_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: pathtopathlink_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.pathtopathlink_id_seq OWNED BY public.pathtopathlink.id;


--
-- Name: platformoptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.platformoptions (
    id integer NOT NULL,
    registrationstrategy integer,
    workspacecreationstrategy integer
);


--
-- Name: prdcfg_optionallink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdcfg_optionallink (
    productbaseline_id integer,
    optionalusagelinks character varying(255)
);


--
-- Name: prdcfg_substitutelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdcfg_substitutelink (
    productbaseline_id integer,
    substitutelinks character varying(255)
);


--
-- Name: prdinstanceiteration_optlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstanceiteration_optlink (
    prdinstancemaster_serialnumber character varying(100),
    configurationitem_id character varying(100),
    workspace_id character varying(100),
    iteration integer,
    optionalusagelinks character varying(255)
);


--
-- Name: prdinstanceiteration_sublink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstanceiteration_sublink (
    prdinstancemaster_serialnumber character varying(100),
    configurationitem_id character varying(100),
    workspace_id character varying(100),
    iteration integer,
    substitutelinks character varying(255)
);


--
-- Name: prdinstiteration_attribute; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstiteration_attribute (
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL,
    instanceattribute_id integer NOT NULL,
    attribute_order integer
);


--
-- Name: prdinstiteration_binres; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstiteration_binres (
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL,
    attachedfile_fullname character varying(722) NOT NULL
);


--
-- Name: prdinstiteration_documentlink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstiteration_documentlink (
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL,
    documentlink_id integer NOT NULL
);


--
-- Name: prdinstiteration_p2plink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstiteration_p2plink (
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    iteration integer NOT NULL,
    pathtopathlink_id integer NOT NULL
);


--
-- Name: prdinstiteration_pathdatamstr; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prdinstiteration_pathdatamstr (
    prdinstanceiteration_iteration integer NOT NULL,
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    pathdatamaster_id integer NOT NULL
);


--
-- Name: productbaseline; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productbaseline (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    description text,
    name character varying(255) NOT NULL,
    type integer,
    author_workspace_id character varying(100),
    author_login character varying(255),
    configurationitem_id character varying(100),
    configurationitem_workspace_id character varying(100),
    documentcollection_id integer,
    partcollection_id integer
);


--
-- Name: productbaseline_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.productbaseline_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: productbaseline_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.productbaseline_id_seq OWNED BY public.productbaseline.id;


--
-- Name: productbaseline_optionallink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productbaseline_optionallink (
    productbaseline_id integer,
    optionalusagelinks character varying(255)
);


--
-- Name: productbaseline_p2plink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productbaseline_p2plink (
    productbaseline_id integer NOT NULL,
    pathtopathlink_id integer NOT NULL
);


--
-- Name: productbaseline_substitutelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productbaseline_substitutelink (
    productbaseline_id integer,
    substitutelinks character varying(255)
);


--
-- Name: productconfiguration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productconfiguration (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    description text,
    name character varying(255) NOT NULL,
    author_workspace_id character varying(100),
    author_login character varying(255),
    configurationitem_id character varying(100),
    configurationitem_workspace_id character varying(100),
    acl_id integer
);


--
-- Name: productconfiguration_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.productconfiguration_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: productconfiguration_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.productconfiguration_id_seq OWNED BY public.productconfiguration.id;


--
-- Name: productinstanceiteration; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productinstanceiteration (
    iteration integer NOT NULL,
    creationdate timestamp without time zone,
    iterationnote character varying(255),
    modificationdate timestamp without time zone,
    author_workspace_id character varying(100),
    author_login character varying(255),
    productbaseline_id integer,
    workspace_id character varying(100) NOT NULL,
    prdinstancemaster_serialnumber character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    documentcollection_id integer,
    partcollection_id integer
);


--
-- Name: productinstancemaster; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.productinstancemaster (
    serialnumber character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    configurationitem_id character varying(100) NOT NULL,
    acl_id integer
);


--
-- Name: providedaccount; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.providedaccount (
    sub character varying(255) NOT NULL,
    login character varying(255) NOT NULL,
    id integer NOT NULL
);


--
-- Name: pusagelink_psubstitutelink; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pusagelink_psubstitutelink (
    partusagelink_id integer NOT NULL,
    partsubstitute_id integer NOT NULL,
    partsubstitute_order integer
);


--
-- Name: query; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.query (
    id integer NOT NULL,
    creationdate timestamp without time zone,
    name character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    pathdata_queryrule_id integer,
    queryrule_id integer
);


--
-- Name: query_grouped_by; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.query_grouped_by (
    query_id integer,
    groupedbylist character varying(255)
);


--
-- Name: query_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.query_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: query_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.query_id_seq OWNED BY public.query.id;


--
-- Name: query_order_by; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.query_order_by (
    query_id integer,
    orderbylist character varying(255)
);


--
-- Name: query_selects; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.query_selects (
    query_id integer,
    selects character varying(255)
);


--
-- Name: querycontext; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.querycontext (
    id integer NOT NULL,
    configurationitemid character varying(255),
    serialnumber character varying(255),
    workspaceid character varying(255),
    query_id integer
);


--
-- Name: querycontext_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.querycontext_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: querycontext_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.querycontext_id_seq OWNED BY public.querycontext.id;


--
-- Name: queryrule; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.queryrule (
    qid integer NOT NULL,
    cond character varying(255),
    field character varying(255),
    id character varying(255),
    operator character varying(255),
    type character varying(255),
    parent_query_rule integer
);


--
-- Name: queryrule_qid_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.queryrule_qid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: queryrule_qid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.queryrule_qid_seq OWNED BY public.queryrule.qid;


--
-- Name: queryrule_values; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.queryrule_values (
    queryrule_id integer,
    value character varying(255),
    value_order integer
);


--
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    name character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: role_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_user (
    role_name character varying(100) NOT NULL,
    role_workspace_id character varying(100) NOT NULL,
    user_login character varying(255) NOT NULL,
    user_workspace_id character varying(100) NOT NULL
);


--
-- Name: role_usergroup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role_usergroup (
    role_name character varying(100) NOT NULL,
    role_workspace_id character varying(100) NOT NULL,
    usergroup_id character varying(100) NOT NULL,
    usergroup_workspace_id character varying(100) NOT NULL
);


--
-- Name: sharedentity; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sharedentity (
    uuid character varying(255) NOT NULL,
    dtype character varying(31),
    creationdate timestamp without time zone,
    expiredate timestamp without time zone,
    password character varying(255),
    author_workspace_id character varying(100),
    author_login character varying(255),
    workspace_id character varying(100) NOT NULL,
    entity_workspace_id character varying(100),
    partmaster_partnumber character varying(100),
    partrevision_version character varying(10),
    documentrevision_version character varying(10),
    documentmaster_id character varying(100)
);


--
-- Name: statechangesubscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.statechangesubscription (
    documentmaster_id character varying(100) NOT NULL,
    documentrevision_version character varying(10) NOT NULL,
    documentmaster_workspace_id character varying(100) NOT NULL,
    subscriber_login character varying(255) NOT NULL,
    subscriber_workspace_id character varying(100) NOT NULL
);


--
-- Name: tag; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tag (
    label character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: tagusergroupsubscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tagusergroupsubscription (
    oniterationchange boolean,
    onstatechange boolean,
    subscriber_id character varying(100) NOT NULL,
    subscriber_workspace_id character varying(100) NOT NULL,
    tag_workspace_id character varying(100) NOT NULL,
    tag_label character varying(100) NOT NULL
);


--
-- Name: tagusersubscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tagusersubscription (
    oniterationchange boolean,
    onstatechange boolean,
    tag_workspace_id character varying(100) NOT NULL,
    tag_label character varying(100) NOT NULL,
    subscriber_login character varying(255) NOT NULL,
    subscriber_workspace_id character varying(100) NOT NULL
);


--
-- Name: task; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task (
    num integer NOT NULL,
    closurecomment character varying(255),
    closuredate timestamp without time zone,
    duration integer,
    instructions text,
    signature text,
    startdate timestamp without time zone,
    status integer,
    targetiteration integer,
    title character varying(255),
    activity_step integer NOT NULL,
    workflow_id integer NOT NULL,
    worker_workspace_id character varying(100),
    worker_login character varying(255)
);


--
-- Name: task_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_user (
    task_num integer NOT NULL,
    activity_step integer NOT NULL,
    workflow_id integer NOT NULL,
    user_login character varying(255) NOT NULL,
    user_workspace_id character varying(100) NOT NULL
);


--
-- Name: task_usergroup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_usergroup (
    task_num integer NOT NULL,
    activity_step integer NOT NULL,
    workflow_id integer NOT NULL,
    usergroup_id character varying(100) NOT NULL,
    usergroup_workspace_id character varying(100) NOT NULL
);


--
-- Name: taskmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.taskmodel (
    num integer NOT NULL,
    duration integer,
    instructions text,
    title character varying(255),
    activitymodel_id integer NOT NULL,
    role_workspace_id character varying(100),
    role_name character varying(100)
);


--
-- Name: userdata; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.userdata (
    login character varying(255) NOT NULL,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: usergroup; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usergroup (
    id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: usergroup_user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usergroup_user (
    usergroup_id character varying(100) NOT NULL,
    usergroup_id_workspace_id character varying(100) NOT NULL,
    user_login character varying(255) NOT NULL,
    user_workspace_id character varying(100) NOT NULL
);


--
-- Name: usergroupmapping; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usergroupmapping (
    login character varying(255) NOT NULL,
    groupname character varying(255)
);


--
-- Name: webhook; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook (
    id integer NOT NULL,
    active boolean,
    name character varying(255),
    workspace_id character varying(100),
    webhookapp_id integer
);


--
-- Name: webhook_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webhook_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webhook_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webhook_id_seq OWNED BY public.webhook.id;


--
-- Name: webhookapp; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhookapp (
    id integer NOT NULL,
    dtype character varying(31),
    auth character varying(255),
    method character varying(255),
    uri character varying(255),
    awsaccount character varying(255),
    awssecret character varying(255),
    region character varying(255),
    topicarn character varying(255)
);


--
-- Name: webhookapp_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.webhookapp_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: webhookapp_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.webhookapp_id_seq OWNED BY public.webhookapp.id;


--
-- Name: workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflow (
    id integer NOT NULL,
    aborteddate timestamp without time zone,
    finallifecyclestate character varying(255)
);


--
-- Name: workflow_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.workflow_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workflow_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.workflow_id_seq OWNED BY public.workflow.id;


--
-- Name: workflowmodel; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workflowmodel (
    id character varying(100) NOT NULL,
    creationdate timestamp without time zone,
    finallifecyclestate character varying(255),
    workspace_id character varying(100) NOT NULL,
    author_workspace_id character varying(100),
    author_login character varying(255),
    acl_id integer
);


--
-- Name: workspace; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace (
    id character varying(100) NOT NULL,
    description text,
    enabled boolean,
    folderlocked boolean,
    admin_login character varying(255)
);


--
-- Name: workspace_aborted_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_aborted_workflow (
    workspace_workflow_id character varying(100) NOT NULL,
    workspace_workflow_workspace_id character varying(100) NOT NULL,
    workflow_id integer NOT NULL
);


--
-- Name: workspace_documenttablecolumn; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_documenttablecolumn (
    workspace_id character varying(100),
    tablecolumn character varying(255),
    documentcolumn_order integer
);


--
-- Name: workspace_parttablecolumn; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_parttablecolumn (
    workspace_id character varying(100),
    tablecolumn character varying(255),
    partcolumn_order integer
);


--
-- Name: workspace_workflow; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspace_workflow (
    id character varying(100) NOT NULL,
    workspace_id character varying(100) NOT NULL,
    workflow_id integer
);


--
-- Name: workspacebackoptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspacebackoptions (
    sendemails boolean,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: workspacefrontoptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspacefrontoptions (
    workspace_id character varying(100) NOT NULL
);


--
-- Name: workspacelog; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspacelog (
    id integer NOT NULL,
    event character varying(255),
    info character varying(255),
    logdate timestamp without time zone,
    userlogin character varying(255),
    workspaceid character varying(255)
);


--
-- Name: workspacelog_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.workspacelog_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: workspacelog_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.workspacelog_id_seq OWNED BY public.workspacelog.id;


--
-- Name: workspaceusergroupmembership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspaceusergroupmembership (
    member_id character varying(100) NOT NULL,
    member_workspace_id character varying(100) NOT NULL,
    readonly boolean,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: workspaceusermembership; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.workspaceusermembership (
    member_login character varying(255) NOT NULL,
    member_workspace_id character varying(100) NOT NULL,
    readonly boolean,
    workspace_id character varying(100) NOT NULL
);


--
-- Name: acl id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acl ALTER COLUMN id SET DEFAULT nextval('public.acl_id_seq'::regclass);


--
-- Name: activitymodel id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel ALTER COLUMN id SET DEFAULT nextval('public.activitymodel_id_seq'::regclass);


--
-- Name: cadinstance id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cadinstance ALTER COLUMN id SET DEFAULT nextval('public.cadinstance_id_seq'::regclass);


--
-- Name: changeissue id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue ALTER COLUMN id SET DEFAULT nextval('public.changeissue_id_seq'::regclass);


--
-- Name: changeorder id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder ALTER COLUMN id SET DEFAULT nextval('public.changeorder_id_seq'::regclass);


--
-- Name: changerequest id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest ALTER COLUMN id SET DEFAULT nextval('public.changerequest_id_seq'::regclass);


--
-- Name: documentbaseline id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentbaseline ALTER COLUMN id SET DEFAULT nextval('public.documentbaseline_id_seq'::regclass);


--
-- Name: documentcollection id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentcollection ALTER COLUMN id SET DEFAULT nextval('public.documentcollection_id_seq'::regclass);


--
-- Name: documentlink id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentlink ALTER COLUMN id SET DEFAULT nextval('public.documentlink_id_seq'::regclass);


--
-- Name: documentlog id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentlog ALTER COLUMN id SET DEFAULT nextval('public.documentlog_id_seq'::regclass);


--
-- Name: effectivity id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.effectivity ALTER COLUMN id SET DEFAULT nextval('public.effectivity_id_seq'::regclass);


--
-- Name: instanceattribute id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattribute ALTER COLUMN id SET DEFAULT nextval('public.instanceattribute_id_seq'::regclass);


--
-- Name: instanceattributetemplate id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattributetemplate ALTER COLUMN id SET DEFAULT nextval('public.instanceattributetemplate_id_seq'::regclass);


--
-- Name: layer id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer ALTER COLUMN id SET DEFAULT nextval('public.layer_id_seq'::regclass);


--
-- Name: marker id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker ALTER COLUMN id SET DEFAULT nextval('public.marker_id_seq'::regclass);


--
-- Name: milestone id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone ALTER COLUMN id SET DEFAULT nextval('public.milestone_id_seq'::regclass);


--
-- Name: modificationnotification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificationnotification ALTER COLUMN id SET DEFAULT nextval('public.modificationnotification_id_seq'::regclass);


--
-- Name: oauthprovider id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauthprovider ALTER COLUMN id SET DEFAULT nextval('public.oauthprovider_id_seq'::regclass);


--
-- Name: partcollection id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partcollection ALTER COLUMN id SET DEFAULT nextval('public.partcollection_id_seq'::regclass);


--
-- Name: partlog id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partlog ALTER COLUMN id SET DEFAULT nextval('public.partlog_id_seq'::regclass);


--
-- Name: partsubstitutelink id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink ALTER COLUMN id SET DEFAULT nextval('public.partsubstitutelink_id_seq'::regclass);


--
-- Name: partusagelink id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink ALTER COLUMN id SET DEFAULT nextval('public.partusagelink_id_seq'::regclass);


--
-- Name: pathdatamaster id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdatamaster ALTER COLUMN id SET DEFAULT nextval('public.pathdatamaster_id_seq'::regclass);


--
-- Name: pathtopathlink id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathtopathlink ALTER COLUMN id SET DEFAULT nextval('public.pathtopathlink_id_seq'::regclass);


--
-- Name: productbaseline id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline ALTER COLUMN id SET DEFAULT nextval('public.productbaseline_id_seq'::regclass);


--
-- Name: productconfiguration id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productconfiguration ALTER COLUMN id SET DEFAULT nextval('public.productconfiguration_id_seq'::regclass);


--
-- Name: query id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query ALTER COLUMN id SET DEFAULT nextval('public.query_id_seq'::regclass);


--
-- Name: querycontext id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.querycontext ALTER COLUMN id SET DEFAULT nextval('public.querycontext_id_seq'::regclass);


--
-- Name: queryrule qid; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queryrule ALTER COLUMN qid SET DEFAULT nextval('public.queryrule_qid_seq'::regclass);


--
-- Name: webhook id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook ALTER COLUMN id SET DEFAULT nextval('public.webhook_id_seq'::regclass);


--
-- Name: webhookapp id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhookapp ALTER COLUMN id SET DEFAULT nextval('public.webhookapp_id_seq'::regclass);


--
-- Name: workflow id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow ALTER COLUMN id SET DEFAULT nextval('public.workflow_id_seq'::regclass);


--
-- Name: workspacelog id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacelog ALTER COLUMN id SET DEFAULT nextval('public.workspacelog_id_seq'::regclass);


--
-- Name: account account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.account
    ADD CONSTRAINT account_pkey PRIMARY KEY (login);


--
-- Name: acl acl_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acl
    ADD CONSTRAINT acl_pkey PRIMARY KEY (id);


--
-- Name: acluserentry acluserentry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acluserentry
    ADD CONSTRAINT acluserentry_pkey PRIMARY KEY (acl_id, principal_login, principal_workspace_id);


--
-- Name: aclusergroupentry aclusergroupentry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aclusergroupentry
    ADD CONSTRAINT aclusergroupentry_pkey PRIMARY KEY (acl_id, principal_workspace_id, principal_id);


--
-- Name: activity activity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity
    ADD CONSTRAINT activity_pkey PRIMARY KEY (step, workflow_id);


--
-- Name: activity_relaunch activity_relaunch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_relaunch
    ADD CONSTRAINT activity_relaunch_pkey PRIMARY KEY (activity_step, activity_workflow_id, relaunch_step, relaunch_workflow_id);


--
-- Name: activitymodel activitymodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel
    ADD CONSTRAINT activitymodel_pkey PRIMARY KEY (id);


--
-- Name: activitymodel_relaunch activitymodel_relaunch_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel_relaunch
    ADD CONSTRAINT activitymodel_relaunch_pkey PRIMARY KEY (activitymodel_id, relaunchactivitymodel_id);


--
-- Name: baselineddocument baselineddocument_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselineddocument
    ADD CONSTRAINT baselineddocument_pkey PRIMARY KEY (documentcollection_id, target_documentmaster_id, target_docrevision_version, target_workspace_id);


--
-- Name: baselinedpart baselinedpart_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselinedpart
    ADD CONSTRAINT baselinedpart_pkey PRIMARY KEY (partcollection_id, target_partmaster_partnumber, target_workspace_id);


--
-- Name: binaryresource binaryresource_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.binaryresource
    ADD CONSTRAINT binaryresource_pkey PRIMARY KEY (fullname);


--
-- Name: cadinstance cadinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cadinstance
    ADD CONSTRAINT cadinstance_pkey PRIMARY KEY (id);


--
-- Name: changeissue_affected_document changeissue_affected_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_document
    ADD CONSTRAINT changeissue_affected_document_pkey PRIMARY KEY (changeissue_id, documentmaster_id, documentrevision_version, documentmaster_workspace_id, iteration);


--
-- Name: changeissue_affected_part changeissue_affected_part_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_part
    ADD CONSTRAINT changeissue_affected_part_pkey PRIMARY KEY (changeissue_id, partmaster_partnumber, partrevision_version, partmaster_workspace_id, iteration);


--
-- Name: changeissue changeissue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue
    ADD CONSTRAINT changeissue_pkey PRIMARY KEY (id);


--
-- Name: changeissue_tag changeissue_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_tag
    ADD CONSTRAINT changeissue_tag_pkey PRIMARY KEY (changeissue_id, tag_label, tag_workspace_id);


--
-- Name: changeorder_affected_document changeorder_affected_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_document
    ADD CONSTRAINT changeorder_affected_document_pkey PRIMARY KEY (changeorder_id, documentmaster_id, documentrevision_version, documentmaster_workspace_id, iteration);


--
-- Name: changeorder_affected_part changeorder_affected_part_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_part
    ADD CONSTRAINT changeorder_affected_part_pkey PRIMARY KEY (changeorder_id, partmaster_partnumber, partrevision_version, partmaster_workspace_id, iteration);


--
-- Name: changeorder_changerequest changeorder_changerequest_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_changerequest
    ADD CONSTRAINT changeorder_changerequest_pkey PRIMARY KEY (changeorder_id, changerequest_id);


--
-- Name: changeorder changeorder_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT changeorder_pkey PRIMARY KEY (id);


--
-- Name: changeorder_tag changeorder_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_tag
    ADD CONSTRAINT changeorder_tag_pkey PRIMARY KEY (changeorder_id, tag_label, tag_workspace_id);


--
-- Name: changereq_affected_document changereq_affected_document_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_document
    ADD CONSTRAINT changereq_affected_document_pkey PRIMARY KEY (changerequest_id, documentmaster_id, documentrevision_version, documentmaster_workspace_id, iteration);


--
-- Name: changereq_affected_part changereq_affected_part_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_part
    ADD CONSTRAINT changereq_affected_part_pkey PRIMARY KEY (changerequest_id, partmaster_partnumber, partrevision_version, partmaster_workspace_id, iteration);


--
-- Name: changerequest_changeissue changerequest_changeissue_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_changeissue
    ADD CONSTRAINT changerequest_changeissue_pkey PRIMARY KEY (changerequest_id, changeissue_id);


--
-- Name: changerequest changerequest_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT changerequest_pkey PRIMARY KEY (id);


--
-- Name: changerequest_tag changerequest_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_tag
    ADD CONSTRAINT changerequest_tag_pkey PRIMARY KEY (changerequest_id, tag_label, tag_workspace_id);


--
-- Name: configurationitem_p2plink configurationitem_p2plink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem_p2plink
    ADD CONSTRAINT configurationitem_p2plink_pkey PRIMARY KEY (configurationitem_id, workspace_id, pathtopathlink_id);


--
-- Name: configurationitem configurationitem_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem
    ADD CONSTRAINT configurationitem_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: conversion conversion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversion
    ADD CONSTRAINT conversion_pkey PRIMARY KEY (workspace_id, iteration, partmaster_partnumber, partrevision_version);


--
-- Name: credential credential_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credential
    ADD CONSTRAINT credential_pkey PRIMARY KEY (login);


--
-- Name: document_aborted_workflow document_aborted_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_aborted_workflow
    ADD CONSTRAINT document_aborted_workflow_pkey PRIMARY KEY (documentmaster_id, documentrevision_version, documentmaster_workspace_id, workflow_id);


--
-- Name: documentbaseline documentbaseline_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentbaseline
    ADD CONSTRAINT documentbaseline_pkey PRIMARY KEY (id);


--
-- Name: documentcollection documentcollection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentcollection
    ADD CONSTRAINT documentcollection_pkey PRIMARY KEY (id);


--
-- Name: documentiteration_attribute documentiteration_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_attribute
    ADD CONSTRAINT documentiteration_attribute_pkey PRIMARY KEY (workspace_id, documentmaster_id, documentrevision_version, iteration, instanceattribute_id);


--
-- Name: documentiteration_binres documentiteration_binres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_binres
    ADD CONSTRAINT documentiteration_binres_pkey PRIMARY KEY (workspace_id, documentmaster_id, documentrevision_version, iteration, attachedfile_fullname);


--
-- Name: documentiteration_documentlink documentiteration_documentlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_documentlink
    ADD CONSTRAINT documentiteration_documentlink_pkey PRIMARY KEY (workspace_id, documentmaster_id, documentrevision_version, iteration, documentlink_id);


--
-- Name: documentiteration documentiteration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration
    ADD CONSTRAINT documentiteration_pkey PRIMARY KEY (iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: documentlink documentlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentlink
    ADD CONSTRAINT documentlink_pkey PRIMARY KEY (id);


--
-- Name: documentlog documentlog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentlog
    ADD CONSTRAINT documentlog_pkey PRIMARY KEY (id);


--
-- Name: documentmaster documentmaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmaster
    ADD CONSTRAINT documentmaster_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: documentmastertemplate_attr documentmastertemplate_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_attr
    ADD CONSTRAINT documentmastertemplate_attr_pkey PRIMARY KEY (workspace_id, documentmastertemplate_id, instanceattributetemplate_id);


--
-- Name: documentmastertemplate_binres documentmastertemplate_binres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_binres
    ADD CONSTRAINT documentmastertemplate_binres_pkey PRIMARY KEY (workspace_id, documentmastertemplate_id, attachedfile_fullname);


--
-- Name: documentmastertemplate documentmastertemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate
    ADD CONSTRAINT documentmastertemplate_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: documentrevision documentrevision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT documentrevision_pkey PRIMARY KEY (version, documentmaster_id, workspace_id);


--
-- Name: documentrevision_tag documentrevision_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision_tag
    ADD CONSTRAINT documentrevision_tag_pkey PRIMARY KEY (documentmaster_id, documentrevision_version, documentmaster_workspace_id, tag_label, tag_workspace_id);


--
-- Name: effectivity effectivity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.effectivity
    ADD CONSTRAINT effectivity_pkey PRIMARY KEY (id);


--
-- Name: folder folder_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT folder_pkey PRIMARY KEY (completepath);


--
-- Name: gcmaccount gcmaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gcmaccount
    ADD CONSTRAINT gcmaccount_pkey PRIMARY KEY (account_login);


--
-- Name: import import_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import
    ADD CONSTRAINT import_pkey PRIMARY KEY (id);


--
-- Name: instanceattribute instanceattribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattribute
    ADD CONSTRAINT instanceattribute_pkey PRIMARY KEY (id);


--
-- Name: instanceattributetemplate instanceattributetemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattributetemplate
    ADD CONSTRAINT instanceattributetemplate_pkey PRIMARY KEY (id);


--
-- Name: iterationchangesubscription iterationchangesubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.iterationchangesubscription
    ADD CONSTRAINT iterationchangesubscription_pkey PRIMARY KEY (documentmaster_id, documentrevision_version, documentmaster_workspace_id, subscriber_login, subscriber_workspace_id);


--
-- Name: layer_marker layer_marker_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_marker
    ADD CONSTRAINT layer_marker_pkey PRIMARY KEY (layer_id, marker_id);


--
-- Name: layer layer_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT layer_pkey PRIMARY KEY (id);


--
-- Name: lov lov_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lov
    ADD CONSTRAINT lov_pkey PRIMARY KEY (name, workspace_id);


--
-- Name: marker_effectivity marker_effectivity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_effectivity
    ADD CONSTRAINT marker_effectivity_pkey PRIMARY KEY (marker_id, effectivity_id);


--
-- Name: marker_partmaster marker_partmaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_partmaster
    ADD CONSTRAINT marker_partmaster_pkey PRIMARY KEY (marker_id, relatedpart_workspace_id, relatedpart_partnumber);


--
-- Name: marker marker_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker
    ADD CONSTRAINT marker_pkey PRIMARY KEY (id);


--
-- Name: milestone milestone_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT milestone_pkey PRIMARY KEY (id);


--
-- Name: modificationnotification modificationnotification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificationnotification
    ADD CONSTRAINT modificationnotification_pkey PRIMARY KEY (id);


--
-- Name: oauthprovider oauthprovider_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.oauthprovider
    ADD CONSTRAINT oauthprovider_pkey PRIMARY KEY (id);


--
-- Name: organization_account organization_account_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_account
    ADD CONSTRAINT organization_account_pkey PRIMARY KEY (organization_name, account_login);


--
-- Name: organization organization_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization
    ADD CONSTRAINT organization_pkey PRIMARY KEY (name);


--
-- Name: part_aborted_workflow part_aborted_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.part_aborted_workflow
    ADD CONSTRAINT part_aborted_workflow_pkey PRIMARY KEY (partmaster_partnumber, partrevision_version, partmaster_workspace_id, workflow_id);


--
-- Name: partcollection partcollection_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partcollection
    ADD CONSTRAINT partcollection_pkey PRIMARY KEY (id);


--
-- Name: partiteration_attribute partiteration_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_attribute
    ADD CONSTRAINT partiteration_attribute_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, instanceattribute_id);


--
-- Name: partiteration_binres partiteration_binres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_binres
    ADD CONSTRAINT partiteration_binres_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, attachedfile_fullname);


--
-- Name: partiteration_documentlink partiteration_documentlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_documentlink
    ADD CONSTRAINT partiteration_documentlink_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, documentlink_id);


--
-- Name: partiteration_geometry partiteration_geometry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_geometry
    ADD CONSTRAINT partiteration_geometry_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, geometry_fullname);


--
-- Name: partiteration_partusagelink partiteration_partusagelink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_partusagelink
    ADD CONSTRAINT partiteration_partusagelink_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, component_id);


--
-- Name: partiteration_pathdata_attr partiteration_pathdata_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_pathdata_attr
    ADD CONSTRAINT partiteration_pathdata_attr_pkey PRIMARY KEY (workspace_id, partmaster_partnumber, partrevision_version, iteration, instanceattribute_template_id);


--
-- Name: partiteration partiteration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration
    ADD CONSTRAINT partiteration_pkey PRIMARY KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partlog partlog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partlog
    ADD CONSTRAINT partlog_pkey PRIMARY KEY (id);


--
-- Name: partmaster partmaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmaster
    ADD CONSTRAINT partmaster_pkey PRIMARY KEY (partnumber, workspace_id);


--
-- Name: partmastertemplate_attr partmastertemplate_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate_attr
    ADD CONSTRAINT partmastertemplate_attr_pkey PRIMARY KEY (workspace_id, partmastertemplate_id, instanceattributetemplate_id);


--
-- Name: partmastertemplate partmastertemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT partmastertemplate_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: partmastertpl_instance_attr partmastertpl_instance_attr_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertpl_instance_attr
    ADD CONSTRAINT partmastertpl_instance_attr_pkey PRIMARY KEY (workspace_id, partmastertemplate_id, instanceattributetemplate_id);


--
-- Name: partrevision_effectivity partrevision_effectivity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_effectivity
    ADD CONSTRAINT partrevision_effectivity_pkey PRIMARY KEY (partmaster_workspace_id, partmaster_partnumber, partrevision_version, effectivity_id);


--
-- Name: partrevision partrevision_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT partrevision_pkey PRIMARY KEY (version, partmaster_partnumber, workspace_id);


--
-- Name: partrevision_tag partrevision_tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_tag
    ADD CONSTRAINT partrevision_tag_pkey PRIMARY KEY (partmaster_partnumber, partrevision_version, partmaster_workspace_id, tag_label, tag_workspace_id);


--
-- Name: partsubstitutelink_cadinstance partsubstitutelink_cadinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink_cadinstance
    ADD CONSTRAINT partsubstitutelink_cadinstance_pkey PRIMARY KEY (partsubstitutelink_id, cadinstance_id);


--
-- Name: partsubstitutelink partsubstitutelink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink
    ADD CONSTRAINT partsubstitutelink_pkey PRIMARY KEY (id);


--
-- Name: partusagelink_cadinstance partusagelink_cadinstance_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink_cadinstance
    ADD CONSTRAINT partusagelink_cadinstance_pkey PRIMARY KEY (partusagelink_id, cadinstance_id);


--
-- Name: partusagelink partusagelink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink
    ADD CONSTRAINT partusagelink_pkey PRIMARY KEY (id);


--
-- Name: passwordrecoveryrequest passwordrecoveryrequest_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.passwordrecoveryrequest
    ADD CONSTRAINT passwordrecoveryrequest_pkey PRIMARY KEY (uuid);


--
-- Name: pathdataiteration_attribute pathdataiteration_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_attribute
    ADD CONSTRAINT pathdataiteration_attribute_pkey PRIMARY KEY (pathdata_iteration, pathdatamaster_id, instanceattribute_id);


--
-- Name: pathdataiteration_binres pathdataiteration_binres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_binres
    ADD CONSTRAINT pathdataiteration_binres_pkey PRIMARY KEY (pathdata_iteration, pathdatamaster_id, attachedfile_fullname);


--
-- Name: pathdataiteration_documentlink pathdataiteration_documentlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_documentlink
    ADD CONSTRAINT pathdataiteration_documentlink_pkey PRIMARY KEY (pathdata_iteration, pathdatamaster_id, documentlink_id);


--
-- Name: pathdataiteration pathdataiteration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration
    ADD CONSTRAINT pathdataiteration_pkey PRIMARY KEY (iteration, pathdatamaster_id);


--
-- Name: pathdatamaster pathdatamaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdatamaster
    ADD CONSTRAINT pathdatamaster_pkey PRIMARY KEY (id);


--
-- Name: pathtopathlink pathtopathlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathtopathlink
    ADD CONSTRAINT pathtopathlink_pkey PRIMARY KEY (id);


--
-- Name: platformoptions platformoptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.platformoptions
    ADD CONSTRAINT platformoptions_pkey PRIMARY KEY (id);


--
-- Name: prdinstiteration_attribute prdinstiteration_attribute_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_attribute
    ADD CONSTRAINT prdinstiteration_attribute_pkey PRIMARY KEY (prdinstancemaster_serialnumber, configurationitem_id, workspace_id, iteration, instanceattribute_id);


--
-- Name: prdinstiteration_binres prdinstiteration_binres_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_binres
    ADD CONSTRAINT prdinstiteration_binres_pkey PRIMARY KEY (prdinstancemaster_serialnumber, configurationitem_id, workspace_id, iteration, attachedfile_fullname);


--
-- Name: prdinstiteration_documentlink prdinstiteration_documentlink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_documentlink
    ADD CONSTRAINT prdinstiteration_documentlink_pkey PRIMARY KEY (prdinstancemaster_serialnumber, configurationitem_id, workspace_id, iteration, documentlink_id);


--
-- Name: prdinstiteration_p2plink prdinstiteration_p2plink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_p2plink
    ADD CONSTRAINT prdinstiteration_p2plink_pkey PRIMARY KEY (prdinstancemaster_serialnumber, configurationitem_id, workspace_id, iteration, pathtopathlink_id);


--
-- Name: prdinstiteration_pathdatamstr prdinstiteration_pathdatamstr_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_pathdatamstr
    ADD CONSTRAINT prdinstiteration_pathdatamstr_pkey PRIMARY KEY (prdinstanceiteration_iteration, prdinstancemaster_serialnumber, configurationitem_id, workspace_id, pathdatamaster_id);


--
-- Name: productbaseline_p2plink productbaseline_p2plink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline_p2plink
    ADD CONSTRAINT productbaseline_p2plink_pkey PRIMARY KEY (productbaseline_id, pathtopathlink_id);


--
-- Name: productbaseline productbaseline_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline
    ADD CONSTRAINT productbaseline_pkey PRIMARY KEY (id);


--
-- Name: productconfiguration productconfiguration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productconfiguration
    ADD CONSTRAINT productconfiguration_pkey PRIMARY KEY (id);


--
-- Name: productinstanceiteration productinstanceiteration_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT productinstanceiteration_pkey PRIMARY KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: productinstancemaster productinstancemaster_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstancemaster
    ADD CONSTRAINT productinstancemaster_pkey PRIMARY KEY (serialnumber, workspace_id, configurationitem_id);


--
-- Name: providedaccount providedaccount_login_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.providedaccount
    ADD CONSTRAINT providedaccount_login_key UNIQUE (login);


--
-- Name: providedaccount providedaccount_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.providedaccount
    ADD CONSTRAINT providedaccount_pkey PRIMARY KEY (sub, login, id);


--
-- Name: pusagelink_psubstitutelink pusagelink_psubstitutelink_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pusagelink_psubstitutelink
    ADD CONSTRAINT pusagelink_psubstitutelink_pkey PRIMARY KEY (partusagelink_id, partsubstitute_id);


--
-- Name: query query_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query
    ADD CONSTRAINT query_pkey PRIMARY KEY (id);


--
-- Name: querycontext querycontext_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.querycontext
    ADD CONSTRAINT querycontext_pkey PRIMARY KEY (id);


--
-- Name: queryrule queryrule_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queryrule
    ADD CONSTRAINT queryrule_pkey PRIMARY KEY (qid);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (name, workspace_id);


--
-- Name: role_user role_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_user
    ADD CONSTRAINT role_user_pkey PRIMARY KEY (role_name, role_workspace_id, user_login, user_workspace_id);


--
-- Name: role_usergroup role_usergroup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_usergroup
    ADD CONSTRAINT role_usergroup_pkey PRIMARY KEY (role_name, role_workspace_id, usergroup_id, usergroup_workspace_id);


--
-- Name: sharedentity sharedentity_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharedentity
    ADD CONSTRAINT sharedentity_pkey PRIMARY KEY (uuid, workspace_id);


--
-- Name: statechangesubscription statechangesubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statechangesubscription
    ADD CONSTRAINT statechangesubscription_pkey PRIMARY KEY (documentmaster_id, documentrevision_version, documentmaster_workspace_id, subscriber_login, subscriber_workspace_id);


--
-- Name: tag tag_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tag
    ADD CONSTRAINT tag_pkey PRIMARY KEY (label, workspace_id);


--
-- Name: tagusergroupsubscription tagusergroupsubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusergroupsubscription
    ADD CONSTRAINT tagusergroupsubscription_pkey PRIMARY KEY (subscriber_id, subscriber_workspace_id, tag_workspace_id, tag_label);


--
-- Name: tagusersubscription tagusersubscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusersubscription
    ADD CONSTRAINT tagusersubscription_pkey PRIMARY KEY (tag_workspace_id, tag_label, subscriber_login, subscriber_workspace_id);


--
-- Name: task task_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_pkey PRIMARY KEY (num, activity_step, workflow_id);


--
-- Name: task_user task_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_user
    ADD CONSTRAINT task_user_pkey PRIMARY KEY (task_num, activity_step, workflow_id, user_login, user_workspace_id);


--
-- Name: task_usergroup task_usergroup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_usergroup
    ADD CONSTRAINT task_usergroup_pkey PRIMARY KEY (task_num, activity_step, workflow_id, usergroup_id, usergroup_workspace_id);


--
-- Name: taskmodel taskmodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taskmodel
    ADD CONSTRAINT taskmodel_pkey PRIMARY KEY (num, activitymodel_id);


--
-- Name: userdata userdata_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.userdata
    ADD CONSTRAINT userdata_pkey PRIMARY KEY (login, workspace_id);


--
-- Name: usergroup usergroup_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroup
    ADD CONSTRAINT usergroup_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: usergroup_user usergroup_user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroup_user
    ADD CONSTRAINT usergroup_user_pkey PRIMARY KEY (usergroup_id, usergroup_id_workspace_id, user_login, user_workspace_id);


--
-- Name: usergroupmapping usergroupmapping_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroupmapping
    ADD CONSTRAINT usergroupmapping_pkey PRIMARY KEY (login);


--
-- Name: webhook webhook_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT webhook_pkey PRIMARY KEY (id);


--
-- Name: webhookapp webhookapp_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhookapp
    ADD CONSTRAINT webhookapp_pkey PRIMARY KEY (id);


--
-- Name: workflow workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflow
    ADD CONSTRAINT workflow_pkey PRIMARY KEY (id);


--
-- Name: workflowmodel workflowmodel_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflowmodel
    ADD CONSTRAINT workflowmodel_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: workspace_aborted_workflow workspace_aborted_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_aborted_workflow
    ADD CONSTRAINT workspace_aborted_workflow_pkey PRIMARY KEY (workspace_workflow_id, workspace_workflow_workspace_id, workflow_id);


--
-- Name: workspace workspace_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace
    ADD CONSTRAINT workspace_pkey PRIMARY KEY (id);


--
-- Name: workspace_workflow workspace_workflow_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_workflow
    ADD CONSTRAINT workspace_workflow_pkey PRIMARY KEY (id, workspace_id);


--
-- Name: workspacebackoptions workspacebackoptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacebackoptions
    ADD CONSTRAINT workspacebackoptions_pkey PRIMARY KEY (workspace_id);


--
-- Name: workspacefrontoptions workspacefrontoptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacefrontoptions
    ADD CONSTRAINT workspacefrontoptions_pkey PRIMARY KEY (workspace_id);


--
-- Name: workspacelog workspacelog_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacelog
    ADD CONSTRAINT workspacelog_pkey PRIMARY KEY (id);


--
-- Name: workspaceusergroupmembership workspaceusergroupmembership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusergroupmembership
    ADD CONSTRAINT workspaceusergroupmembership_pkey PRIMARY KEY (member_id, member_workspace_id, workspace_id);


--
-- Name: workspaceusermembership workspaceusermembership_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusermembership
    ADD CONSTRAINT workspaceusermembership_pkey PRIMARY KEY (member_login, member_workspace_id, workspace_id);


--
-- Name: index_doc_fullname; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_doc_fullname ON public.documentiteration_binres USING btree (attachedfile_fullname);


--
-- Name: index_doc_wks; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_doc_wks ON public.documentmaster USING btree (workspace_id);


--
-- Name: index_doc_wks_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_doc_wks_id ON public.documentrevision USING btree (workspace_id, documentmaster_id);


--
-- Name: index_doc_wks_id_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_doc_wks_id_version ON public.documentiteration USING btree (workspace_id, documentmaster_id, documentrevision_version);


--
-- Name: index_part_fullname; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_part_fullname ON public.partiteration_binres USING btree (attachedfile_fullname);


--
-- Name: index_part_wks; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_part_wks ON public.partmaster USING btree (workspace_id);


--
-- Name: index_part_wks_partnumber; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_part_wks_partnumber ON public.partrevision USING btree (workspace_id, partmaster_partnumber);


--
-- Name: index_part_wks_partnumber_version; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX index_part_wks_partnumber_version ON public.partiteration USING btree (workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: acluserentry fk_acluserentry_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acluserentry
    ADD CONSTRAINT fk_acluserentry_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: acluserentry fk_acluserentry_principal_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.acluserentry
    ADD CONSTRAINT fk_acluserentry_principal_login FOREIGN KEY (principal_login, principal_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: aclusergroupentry fk_aclusergroupentry_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aclusergroupentry
    ADD CONSTRAINT fk_aclusergroupentry_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: aclusergroupentry fk_aclusergroupentry_principal_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aclusergroupentry
    ADD CONSTRAINT fk_aclusergroupentry_principal_id FOREIGN KEY (principal_id, principal_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: activity_relaunch fk_activity_relaunch_activity_step; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_relaunch
    ADD CONSTRAINT fk_activity_relaunch_activity_step FOREIGN KEY (activity_step, activity_workflow_id) REFERENCES public.activity(step, workflow_id);


--
-- Name: activity_relaunch fk_activity_relaunch_relaunch_step; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity_relaunch
    ADD CONSTRAINT fk_activity_relaunch_relaunch_step FOREIGN KEY (relaunch_step, relaunch_workflow_id) REFERENCES public.activity(step, workflow_id);


--
-- Name: activity fk_activity_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activity
    ADD CONSTRAINT fk_activity_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: activitymodel_relaunch fk_activitymodel_relaunch_activitymodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel_relaunch
    ADD CONSTRAINT fk_activitymodel_relaunch_activitymodel_id FOREIGN KEY (activitymodel_id) REFERENCES public.activitymodel(id);


--
-- Name: activitymodel_relaunch fk_activitymodel_relaunch_relaunchactivitymodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel_relaunch
    ADD CONSTRAINT fk_activitymodel_relaunch_relaunchactivitymodel_id FOREIGN KEY (relaunchactivitymodel_id) REFERENCES public.activitymodel(id);


--
-- Name: activitymodel fk_activitymodel_workflowmodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.activitymodel
    ADD CONSTRAINT fk_activitymodel_workflowmodel_id FOREIGN KEY (workflowmodel_id, workspace_id) REFERENCES public.workflowmodel(id, workspace_id);


--
-- Name: attribute_namevalue fk_attribute_namevalue_attribute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attribute_namevalue
    ADD CONSTRAINT fk_attribute_namevalue_attribute_id FOREIGN KEY (attribute_id) REFERENCES public.instanceattribute(id);


--
-- Name: baselineddocument fk_baselineddocument_documentcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselineddocument
    ADD CONSTRAINT fk_baselineddocument_documentcollection_id FOREIGN KEY (documentcollection_id) REFERENCES public.documentcollection(id);


--
-- Name: baselineddocument fk_baselineddocument_target_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselineddocument
    ADD CONSTRAINT fk_baselineddocument_target_iteration FOREIGN KEY (target_iteration, target_workspace_id, target_docrevision_version, target_documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: baselinedpart fk_baselinedpart_partcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselinedpart
    ADD CONSTRAINT fk_baselinedpart_partcollection_id FOREIGN KEY (partcollection_id) REFERENCES public.partcollection(id);


--
-- Name: baselinedpart fk_baselinedpart_target_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.baselinedpart
    ADD CONSTRAINT fk_baselinedpart_target_iteration FOREIGN KEY (target_iteration, target_workspace_id, target_partmaster_partnumber, target_partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: changeissue fk_changeissue_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue
    ADD CONSTRAINT fk_changeissue_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: changeissue_affected_document fk_changeissue_affected_document_changeissue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_document
    ADD CONSTRAINT fk_changeissue_affected_document_changeissue_id FOREIGN KEY (changeissue_id) REFERENCES public.changeissue(id);


--
-- Name: changeissue_affected_document fk_changeissue_affected_document_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_document
    ADD CONSTRAINT fk_changeissue_affected_document_iteration FOREIGN KEY (iteration, documentmaster_workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: changeissue_affected_part fk_changeissue_affected_part_changeissue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_part
    ADD CONSTRAINT fk_changeissue_affected_part_changeissue_id FOREIGN KEY (changeissue_id) REFERENCES public.changeissue(id);


--
-- Name: changeissue_affected_part fk_changeissue_affected_part_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_affected_part
    ADD CONSTRAINT fk_changeissue_affected_part_iteration FOREIGN KEY (iteration, partmaster_workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: changeissue fk_changeissue_assignee_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue
    ADD CONSTRAINT fk_changeissue_assignee_login FOREIGN KEY (assignee_login, assignee_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changeissue fk_changeissue_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue
    ADD CONSTRAINT fk_changeissue_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changeissue_tag fk_changeissue_tag_changeissue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_tag
    ADD CONSTRAINT fk_changeissue_tag_changeissue_id FOREIGN KEY (changeissue_id) REFERENCES public.changeissue(id);


--
-- Name: changeissue_tag fk_changeissue_tag_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue_tag
    ADD CONSTRAINT fk_changeissue_tag_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: changeissue fk_changeissue_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeissue
    ADD CONSTRAINT fk_changeissue_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: changeorder fk_changeorder_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT fk_changeorder_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: changeorder_affected_document fk_changeorder_affected_document_changeorder_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_document
    ADD CONSTRAINT fk_changeorder_affected_document_changeorder_id FOREIGN KEY (changeorder_id) REFERENCES public.changeorder(id);


--
-- Name: changeorder_affected_document fk_changeorder_affected_document_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_document
    ADD CONSTRAINT fk_changeorder_affected_document_iteration FOREIGN KEY (iteration, documentmaster_workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: changeorder_affected_part fk_changeorder_affected_part_changeorder_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_part
    ADD CONSTRAINT fk_changeorder_affected_part_changeorder_id FOREIGN KEY (changeorder_id) REFERENCES public.changeorder(id);


--
-- Name: changeorder_affected_part fk_changeorder_affected_part_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_affected_part
    ADD CONSTRAINT fk_changeorder_affected_part_iteration FOREIGN KEY (iteration, partmaster_workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: changeorder fk_changeorder_assignee_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT fk_changeorder_assignee_login FOREIGN KEY (assignee_login, assignee_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changeorder fk_changeorder_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT fk_changeorder_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changeorder_changerequest fk_changeorder_changerequest_changeorder_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_changerequest
    ADD CONSTRAINT fk_changeorder_changerequest_changeorder_id FOREIGN KEY (changeorder_id) REFERENCES public.changeorder(id);


--
-- Name: changeorder_changerequest fk_changeorder_changerequest_changerequest_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_changerequest
    ADD CONSTRAINT fk_changeorder_changerequest_changerequest_id FOREIGN KEY (changerequest_id) REFERENCES public.changerequest(id);


--
-- Name: changeorder fk_changeorder_milestone_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT fk_changeorder_milestone_id FOREIGN KEY (milestone_id) REFERENCES public.milestone(id);


--
-- Name: changeorder_tag fk_changeorder_tag_changeorder_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_tag
    ADD CONSTRAINT fk_changeorder_tag_changeorder_id FOREIGN KEY (changeorder_id) REFERENCES public.changeorder(id);


--
-- Name: changeorder_tag fk_changeorder_tag_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder_tag
    ADD CONSTRAINT fk_changeorder_tag_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: changeorder fk_changeorder_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changeorder
    ADD CONSTRAINT fk_changeorder_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: changereq_affected_document fk_changereq_affected_document_changerequest_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_document
    ADD CONSTRAINT fk_changereq_affected_document_changerequest_id FOREIGN KEY (changerequest_id) REFERENCES public.changerequest(id);


--
-- Name: changereq_affected_document fk_changereq_affected_document_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_document
    ADD CONSTRAINT fk_changereq_affected_document_iteration FOREIGN KEY (iteration, documentmaster_workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: changereq_affected_part fk_changereq_affected_part_changerequest_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_part
    ADD CONSTRAINT fk_changereq_affected_part_changerequest_id FOREIGN KEY (changerequest_id) REFERENCES public.changerequest(id);


--
-- Name: changereq_affected_part fk_changereq_affected_part_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changereq_affected_part
    ADD CONSTRAINT fk_changereq_affected_part_iteration FOREIGN KEY (iteration, partmaster_workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: changerequest fk_changerequest_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT fk_changerequest_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: changerequest fk_changerequest_assignee_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT fk_changerequest_assignee_login FOREIGN KEY (assignee_login, assignee_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changerequest fk_changerequest_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT fk_changerequest_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: changerequest_changeissue fk_changerequest_changeissue_changeissue_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_changeissue
    ADD CONSTRAINT fk_changerequest_changeissue_changeissue_id FOREIGN KEY (changeissue_id) REFERENCES public.changeissue(id);


--
-- Name: changerequest_changeissue fk_changerequest_changeissue_changerequest_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_changeissue
    ADD CONSTRAINT fk_changerequest_changeissue_changerequest_id FOREIGN KEY (changerequest_id) REFERENCES public.changerequest(id);


--
-- Name: changerequest fk_changerequest_milestone_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT fk_changerequest_milestone_id FOREIGN KEY (milestone_id) REFERENCES public.milestone(id);


--
-- Name: changerequest_tag fk_changerequest_tag_changerequest_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_tag
    ADD CONSTRAINT fk_changerequest_tag_changerequest_id FOREIGN KEY (changerequest_id) REFERENCES public.changerequest(id);


--
-- Name: changerequest_tag fk_changerequest_tag_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest_tag
    ADD CONSTRAINT fk_changerequest_tag_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: changerequest fk_changerequest_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.changerequest
    ADD CONSTRAINT fk_changerequest_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: configurationitem fk_configurationitem_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem
    ADD CONSTRAINT fk_configurationitem_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: configurationitem_p2plink fk_configurationitem_p2plink_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem_p2plink
    ADD CONSTRAINT fk_configurationitem_p2plink_configurationitem_id FOREIGN KEY (configurationitem_id, workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: configurationitem_p2plink fk_configurationitem_p2plink_pathtopathlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem_p2plink
    ADD CONSTRAINT fk_configurationitem_p2plink_pathtopathlink_id FOREIGN KEY (pathtopathlink_id) REFERENCES public.pathtopathlink(id);


--
-- Name: configurationitem fk_configurationitem_partmaster_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem
    ADD CONSTRAINT fk_configurationitem_partmaster_partnumber FOREIGN KEY (partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: configurationitem fk_configurationitem_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configurationitem
    ADD CONSTRAINT fk_configurationitem_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: conversion fk_conversion_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversion
    ADD CONSTRAINT fk_conversion_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: document_aborted_workflow fk_document_aborted_workflow_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_aborted_workflow
    ADD CONSTRAINT fk_document_aborted_workflow_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, documentmaster_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: document_aborted_workflow fk_document_aborted_workflow_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_aborted_workflow
    ADD CONSTRAINT fk_document_aborted_workflow_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: documentbaseline fk_documentbaseline_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentbaseline
    ADD CONSTRAINT fk_documentbaseline_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentbaseline fk_documentbaseline_documentcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentbaseline
    ADD CONSTRAINT fk_documentbaseline_documentcollection_id FOREIGN KEY (documentcollection_id) REFERENCES public.documentcollection(id);


--
-- Name: documentcollection fk_documentcollection_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentcollection
    ADD CONSTRAINT fk_documentcollection_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentiteration_attribute fk_documentiteration_attribute_instanceattribute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_attribute
    ADD CONSTRAINT fk_documentiteration_attribute_instanceattribute_id FOREIGN KEY (instanceattribute_id) REFERENCES public.instanceattribute(id);


--
-- Name: documentiteration_attribute fk_documentiteration_attribute_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_attribute
    ADD CONSTRAINT fk_documentiteration_attribute_iteration FOREIGN KEY (iteration, workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: documentiteration fk_documentiteration_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration
    ADD CONSTRAINT fk_documentiteration_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentiteration_binres fk_documentiteration_binres_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_binres
    ADD CONSTRAINT fk_documentiteration_binres_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: documentiteration_binres fk_documentiteration_binres_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_binres
    ADD CONSTRAINT fk_documentiteration_binres_iteration FOREIGN KEY (iteration, workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: documentiteration_documentlink fk_documentiteration_documentlink_documentlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_documentlink
    ADD CONSTRAINT fk_documentiteration_documentlink_documentlink_id FOREIGN KEY (documentlink_id) REFERENCES public.documentlink(id);


--
-- Name: documentiteration_documentlink fk_documentiteration_documentlink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration_documentlink
    ADD CONSTRAINT fk_documentiteration_documentlink_iteration FOREIGN KEY (iteration, workspace_id, documentrevision_version, documentmaster_id) REFERENCES public.documentiteration(iteration, workspace_id, documentrevision_version, documentmaster_id);


--
-- Name: documentiteration fk_documentiteration_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentiteration
    ADD CONSTRAINT fk_documentiteration_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: documentlink fk_documentlink_target_docrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentlink
    ADD CONSTRAINT fk_documentlink_target_docrevision_version FOREIGN KEY (target_docrevision_version, target_documentmaster_id, target_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: documentmaster fk_documentmaster_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmaster
    ADD CONSTRAINT fk_documentmaster_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentmaster fk_documentmaster_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmaster
    ADD CONSTRAINT fk_documentmaster_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: documentmastertemplate fk_documentmastertemplate_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate
    ADD CONSTRAINT fk_documentmastertemplate_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: documentmastertemplate_attr fk_documentmastertemplate_attr_documentmastertemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_attr
    ADD CONSTRAINT fk_documentmastertemplate_attr_documentmastertemplate_id FOREIGN KEY (documentmastertemplate_id, workspace_id) REFERENCES public.documentmastertemplate(id, workspace_id);


--
-- Name: documentmastertemplate_attr fk_documentmastertemplate_attr_instanceattributetemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_attr
    ADD CONSTRAINT fk_documentmastertemplate_attr_instanceattributetemplate_id FOREIGN KEY (instanceattributetemplate_id) REFERENCES public.instanceattributetemplate(id);


--
-- Name: documentmastertemplate fk_documentmastertemplate_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate
    ADD CONSTRAINT fk_documentmastertemplate_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentmastertemplate_binres fk_documentmastertemplate_binres_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_binres
    ADD CONSTRAINT fk_documentmastertemplate_binres_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: documentmastertemplate_binres fk_documentmastertemplate_binres_documentmastertemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate_binres
    ADD CONSTRAINT fk_documentmastertemplate_binres_documentmastertemplate_id FOREIGN KEY (documentmastertemplate_id, workspace_id) REFERENCES public.documentmastertemplate(id, workspace_id);


--
-- Name: documentmastertemplate fk_documentmastertemplate_workflowmodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate
    ADD CONSTRAINT fk_documentmastertemplate_workflowmodel_id FOREIGN KEY (workflowmodel_id, workflowmodel_workspace_id) REFERENCES public.workflowmodel(id, workspace_id);


--
-- Name: documentmastertemplate fk_documentmastertemplate_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentmastertemplate
    ADD CONSTRAINT fk_documentmastertemplate_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: documentrevision fk_documentrevision_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: documentrevision fk_documentrevision_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentrevision fk_documentrevision_checkoutuser_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_checkoutuser_login FOREIGN KEY (checkoutuser_login, checkoutuser_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentrevision fk_documentrevision_documentmaster_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_documentmaster_id FOREIGN KEY (documentmaster_id, workspace_id) REFERENCES public.documentmaster(id, workspace_id);


--
-- Name: documentrevision fk_documentrevision_location_completepath; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_location_completepath FOREIGN KEY (location_completepath) REFERENCES public.folder(completepath);


--
-- Name: documentrevision fk_documentrevision_obsolete_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_obsolete_user_login FOREIGN KEY (obsolete_user_login, obsolete_user_workspace) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentrevision fk_documentrevision_release_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_release_user_login FOREIGN KEY (release_user_login, release_user_workspace) REFERENCES public.userdata(login, workspace_id);


--
-- Name: documentrevision_tag fk_documentrevision_tag_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision_tag
    ADD CONSTRAINT fk_documentrevision_tag_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, documentmaster_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: documentrevision_tag fk_documentrevision_tag_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision_tag
    ADD CONSTRAINT fk_documentrevision_tag_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: documentrevision fk_documentrevision_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documentrevision
    ADD CONSTRAINT fk_documentrevision_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: effectivity fk_effectivity_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.effectivity
    ADD CONSTRAINT fk_effectivity_configurationitem_id FOREIGN KEY (configurationitem_id, configurationitem_workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: folder fk_folder_parentfolder_completepath; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.folder
    ADD CONSTRAINT fk_folder_parentfolder_completepath FOREIGN KEY (parentfolder_completepath) REFERENCES public.folder(completepath);


--
-- Name: gcmaccount fk_gcmaccount_account_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.gcmaccount
    ADD CONSTRAINT fk_gcmaccount_account_login FOREIGN KEY (account_login) REFERENCES public.account(login);


--
-- Name: import_error fk_import_error_import_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_error
    ADD CONSTRAINT fk_import_error_import_id FOREIGN KEY (import_id) REFERENCES public.import(id);


--
-- Name: import fk_import_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import
    ADD CONSTRAINT fk_import_user_login FOREIGN KEY (user_login, user_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: import_warning fk_import_warning_import_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.import_warning
    ADD CONSTRAINT fk_import_warning_import_id FOREIGN KEY (import_id) REFERENCES public.import(id);


--
-- Name: instanceattribute fk_instanceattribute_partmaster_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattribute
    ADD CONSTRAINT fk_instanceattribute_partmaster_partnumber FOREIGN KEY (partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: instanceattributetemplate fk_instanceattributetemplate_lov_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instanceattributetemplate
    ADD CONSTRAINT fk_instanceattributetemplate_lov_name FOREIGN KEY (lov_name, lov_workspace_id) REFERENCES public.lov(name, workspace_id);


--
-- Name: iterationchangesubscription fk_iterationchangesubscription_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.iterationchangesubscription
    ADD CONSTRAINT fk_iterationchangesubscription_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, documentmaster_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: iterationchangesubscription fk_iterationchangesubscription_subscriber_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.iterationchangesubscription
    ADD CONSTRAINT fk_iterationchangesubscription_subscriber_login FOREIGN KEY (subscriber_login, subscriber_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: layer fk_layer_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT fk_layer_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: layer fk_layer_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer
    ADD CONSTRAINT fk_layer_configurationitem_id FOREIGN KEY (configurationitem_id, configurationitem_workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: layer_marker fk_layer_marker_layer_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_marker
    ADD CONSTRAINT fk_layer_marker_layer_id FOREIGN KEY (layer_id) REFERENCES public.layer(id);


--
-- Name: layer_marker fk_layer_marker_marker_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.layer_marker
    ADD CONSTRAINT fk_layer_marker_marker_id FOREIGN KEY (marker_id) REFERENCES public.marker(id);


--
-- Name: lov_namevalue fk_lov_namevalue_lov_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lov_namevalue
    ADD CONSTRAINT fk_lov_namevalue_lov_name FOREIGN KEY (lov_name, lov_workspace_id) REFERENCES public.lov(name, workspace_id);


--
-- Name: lov fk_lov_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lov
    ADD CONSTRAINT fk_lov_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: marker fk_marker_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker
    ADD CONSTRAINT fk_marker_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: marker_effectivity fk_marker_effectivity_effectivity_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_effectivity
    ADD CONSTRAINT fk_marker_effectivity_effectivity_id FOREIGN KEY (effectivity_id) REFERENCES public.effectivity(id);


--
-- Name: marker_effectivity fk_marker_effectivity_marker_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_effectivity
    ADD CONSTRAINT fk_marker_effectivity_marker_id FOREIGN KEY (marker_id) REFERENCES public.marker(id);


--
-- Name: marker_partmaster fk_marker_partmaster_marker_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_partmaster
    ADD CONSTRAINT fk_marker_partmaster_marker_id FOREIGN KEY (marker_id) REFERENCES public.marker(id);


--
-- Name: marker_partmaster fk_marker_partmaster_relatedpart_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.marker_partmaster
    ADD CONSTRAINT fk_marker_partmaster_relatedpart_partnumber FOREIGN KEY (relatedpart_partnumber, relatedpart_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: milestone fk_milestone_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT fk_milestone_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: milestone fk_milestone_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.milestone
    ADD CONSTRAINT fk_milestone_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: modificationnotification fk_modificationnotification_ackauthor_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificationnotification
    ADD CONSTRAINT fk_modificationnotification_ackauthor_login FOREIGN KEY (ackauthor_login, ackauthor_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: modificationnotification fk_modificationnotification_impacted_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificationnotification
    ADD CONSTRAINT fk_modificationnotification_impacted_iteration FOREIGN KEY (impacted_iteration, impacted_workspace_id, impacted_partmaster_partnumber, impacted_partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: modificationnotification fk_modificationnotification_modified_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificationnotification
    ADD CONSTRAINT fk_modificationnotification_modified_iteration FOREIGN KEY (modified_iteration, modified_workspace_id, modified_partmaster_partnumber, modified_partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: organization_account fk_organization_account_account_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_account
    ADD CONSTRAINT fk_organization_account_account_login FOREIGN KEY (account_login) REFERENCES public.account(login);


--
-- Name: organization_account fk_organization_account_organization_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_account
    ADD CONSTRAINT fk_organization_account_organization_name FOREIGN KEY (organization_name) REFERENCES public.organization(name);


--
-- Name: organization fk_organization_owner_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization
    ADD CONSTRAINT fk_organization_owner_login FOREIGN KEY (owner_login) REFERENCES public.account(login);


--
-- Name: part_aborted_workflow fk_part_aborted_workflow_partrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.part_aborted_workflow
    ADD CONSTRAINT fk_part_aborted_workflow_partrevision_version FOREIGN KEY (partrevision_version, partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partrevision(version, partmaster_partnumber, workspace_id);


--
-- Name: part_aborted_workflow fk_part_aborted_workflow_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.part_aborted_workflow
    ADD CONSTRAINT fk_part_aborted_workflow_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: partcollection fk_partcollection_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partcollection
    ADD CONSTRAINT fk_partcollection_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partiteration_attribute fk_partiteration_attribute_instanceattribute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_attribute
    ADD CONSTRAINT fk_partiteration_attribute_instanceattribute_id FOREIGN KEY (instanceattribute_id) REFERENCES public.instanceattribute(id);


--
-- Name: partiteration_attribute fk_partiteration_attribute_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_attribute
    ADD CONSTRAINT fk_partiteration_attribute_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partiteration fk_partiteration_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration
    ADD CONSTRAINT fk_partiteration_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partiteration_binres fk_partiteration_binres_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_binres
    ADD CONSTRAINT fk_partiteration_binres_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: partiteration_binres fk_partiteration_binres_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_binres
    ADD CONSTRAINT fk_partiteration_binres_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partiteration_documentlink fk_partiteration_documentlink_documentlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_documentlink
    ADD CONSTRAINT fk_partiteration_documentlink_documentlink_id FOREIGN KEY (documentlink_id) REFERENCES public.documentlink(id);


--
-- Name: partiteration_documentlink fk_partiteration_documentlink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_documentlink
    ADD CONSTRAINT fk_partiteration_documentlink_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partiteration_geometry fk_partiteration_geometry_geometry_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_geometry
    ADD CONSTRAINT fk_partiteration_geometry_geometry_fullname FOREIGN KEY (geometry_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: partiteration_geometry fk_partiteration_geometry_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_geometry
    ADD CONSTRAINT fk_partiteration_geometry_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partiteration fk_partiteration_nativecadfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration
    ADD CONSTRAINT fk_partiteration_nativecadfile_fullname FOREIGN KEY (nativecadfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: partiteration fk_partiteration_partrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration
    ADD CONSTRAINT fk_partiteration_partrevision_version FOREIGN KEY (partrevision_version, partmaster_partnumber, workspace_id) REFERENCES public.partrevision(version, partmaster_partnumber, workspace_id);


--
-- Name: partiteration_partusagelink fk_partiteration_partusagelink_component_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_partusagelink
    ADD CONSTRAINT fk_partiteration_partusagelink_component_id FOREIGN KEY (component_id) REFERENCES public.partusagelink(id);


--
-- Name: partiteration_partusagelink fk_partiteration_partusagelink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_partusagelink
    ADD CONSTRAINT fk_partiteration_partusagelink_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partiteration_pathdata_attr fk_partiteration_pathdata_attr_instanceattribute_template_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_pathdata_attr
    ADD CONSTRAINT fk_partiteration_pathdata_attr_instanceattribute_template_id FOREIGN KEY (instanceattribute_template_id) REFERENCES public.instanceattributetemplate(id);


--
-- Name: partiteration_pathdata_attr fk_partiteration_pathdata_attr_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partiteration_pathdata_attr
    ADD CONSTRAINT fk_partiteration_pathdata_attr_iteration FOREIGN KEY (iteration, workspace_id, partmaster_partnumber, partrevision_version) REFERENCES public.partiteration(iteration, workspace_id, partmaster_partnumber, partrevision_version);


--
-- Name: partmaster_alternate fk_partmaster_alternate_partmaster_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmaster_alternate
    ADD CONSTRAINT fk_partmaster_alternate_partmaster_partnumber FOREIGN KEY (partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: partmaster fk_partmaster_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmaster
    ADD CONSTRAINT fk_partmaster_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partmaster fk_partmaster_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmaster
    ADD CONSTRAINT fk_partmaster_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: partmastertemplate fk_partmastertemplate_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT fk_partmastertemplate_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: partmastertemplate fk_partmastertemplate_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT fk_partmastertemplate_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: partmastertemplate_attr fk_partmastertemplate_attr_instanceattributetemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate_attr
    ADD CONSTRAINT fk_partmastertemplate_attr_instanceattributetemplate_id FOREIGN KEY (instanceattributetemplate_id) REFERENCES public.instanceattributetemplate(id);


--
-- Name: partmastertemplate_attr fk_partmastertemplate_attr_partmastertemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate_attr
    ADD CONSTRAINT fk_partmastertemplate_attr_partmastertemplate_id FOREIGN KEY (partmastertemplate_id, workspace_id) REFERENCES public.partmastertemplate(id, workspace_id);


--
-- Name: partmastertemplate fk_partmastertemplate_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT fk_partmastertemplate_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partmastertemplate fk_partmastertemplate_workflowmodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT fk_partmastertemplate_workflowmodel_id FOREIGN KEY (workflowmodel_id, workflowmodel_workspace_id) REFERENCES public.workflowmodel(id, workspace_id);


--
-- Name: partmastertemplate fk_partmastertemplate_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertemplate
    ADD CONSTRAINT fk_partmastertemplate_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: partmastertpl_instance_attr fk_partmastertpl_instance_attr_instanceattributetemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertpl_instance_attr
    ADD CONSTRAINT fk_partmastertpl_instance_attr_instanceattributetemplate_id FOREIGN KEY (instanceattributetemplate_id) REFERENCES public.instanceattributetemplate(id);


--
-- Name: partmastertpl_instance_attr fk_partmastertpl_instance_attr_partmastertemplate_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partmastertpl_instance_attr
    ADD CONSTRAINT fk_partmastertpl_instance_attr_partmastertemplate_id FOREIGN KEY (partmastertemplate_id, workspace_id) REFERENCES public.partmastertemplate(id, workspace_id);


--
-- Name: partrevision fk_partrevision_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: partrevision fk_partrevision_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partrevision fk_partrevision_checkoutuser_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_checkoutuser_login FOREIGN KEY (checkoutuser_login, checkoutuser_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partrevision_effectivity fk_partrevision_effectivity_effectivity_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_effectivity
    ADD CONSTRAINT fk_partrevision_effectivity_effectivity_id FOREIGN KEY (effectivity_id) REFERENCES public.effectivity(id);


--
-- Name: partrevision_effectivity fk_partrevision_effectivity_partrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_effectivity
    ADD CONSTRAINT fk_partrevision_effectivity_partrevision_version FOREIGN KEY (partrevision_version, partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partrevision(version, partmaster_partnumber, workspace_id);


--
-- Name: partrevision fk_partrevision_obsolete_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_obsolete_user_login FOREIGN KEY (obsolete_user_login, obsolete_user_workspace) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partrevision fk_partrevision_partmaster_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_partmaster_partnumber FOREIGN KEY (partmaster_partnumber, workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: partrevision fk_partrevision_release_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_release_user_login FOREIGN KEY (release_user_login, release_user_workspace) REFERENCES public.userdata(login, workspace_id);


--
-- Name: partrevision_tag fk_partrevision_tag_partrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_tag
    ADD CONSTRAINT fk_partrevision_tag_partrevision_version FOREIGN KEY (partrevision_version, partmaster_partnumber, partmaster_workspace_id) REFERENCES public.partrevision(version, partmaster_partnumber, workspace_id);


--
-- Name: partrevision_tag fk_partrevision_tag_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision_tag
    ADD CONSTRAINT fk_partrevision_tag_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: partrevision fk_partrevision_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partrevision
    ADD CONSTRAINT fk_partrevision_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: partsubstitutelink_cadinstance fk_partsubstitutelink_cadinstance_cadinstance_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink_cadinstance
    ADD CONSTRAINT fk_partsubstitutelink_cadinstance_cadinstance_id FOREIGN KEY (cadinstance_id) REFERENCES public.cadinstance(id);


--
-- Name: partsubstitutelink_cadinstance fk_partsubstitutelink_cadinstance_partsubstitutelink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink_cadinstance
    ADD CONSTRAINT fk_partsubstitutelink_cadinstance_partsubstitutelink_id FOREIGN KEY (partsubstitutelink_id) REFERENCES public.partsubstitutelink(id);


--
-- Name: partsubstitutelink fk_partsubstitutelink_substitute_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partsubstitutelink
    ADD CONSTRAINT fk_partsubstitutelink_substitute_partnumber FOREIGN KEY (substitute_partnumber, substitute_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: partusagelink_cadinstance fk_partusagelink_cadinstance_cadinstance_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink_cadinstance
    ADD CONSTRAINT fk_partusagelink_cadinstance_cadinstance_id FOREIGN KEY (cadinstance_id) REFERENCES public.cadinstance(id);


--
-- Name: partusagelink_cadinstance fk_partusagelink_cadinstance_partusagelink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink_cadinstance
    ADD CONSTRAINT fk_partusagelink_cadinstance_partusagelink_id FOREIGN KEY (partusagelink_id) REFERENCES public.partusagelink(id);


--
-- Name: partusagelink fk_partusagelink_component_partnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partusagelink
    ADD CONSTRAINT fk_partusagelink_component_partnumber FOREIGN KEY (component_partnumber, component_workspace_id) REFERENCES public.partmaster(partnumber, workspace_id);


--
-- Name: pathdataiteration_attribute fk_pathdataiteration_attribute_instanceattribute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_attribute
    ADD CONSTRAINT fk_pathdataiteration_attribute_instanceattribute_id FOREIGN KEY (instanceattribute_id) REFERENCES public.instanceattribute(id);


--
-- Name: pathdataiteration_attribute fk_pathdataiteration_attribute_pathdata_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_attribute
    ADD CONSTRAINT fk_pathdataiteration_attribute_pathdata_iteration FOREIGN KEY (pathdata_iteration, pathdatamaster_id) REFERENCES public.pathdataiteration(iteration, pathdatamaster_id);


--
-- Name: pathdataiteration_binres fk_pathdataiteration_binres_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_binres
    ADD CONSTRAINT fk_pathdataiteration_binres_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: pathdataiteration_binres fk_pathdataiteration_binres_pathdata_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_binres
    ADD CONSTRAINT fk_pathdataiteration_binres_pathdata_iteration FOREIGN KEY (pathdata_iteration, pathdatamaster_id) REFERENCES public.pathdataiteration(iteration, pathdatamaster_id);


--
-- Name: pathdataiteration_documentlink fk_pathdataiteration_documentlink_documentlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_documentlink
    ADD CONSTRAINT fk_pathdataiteration_documentlink_documentlink_id FOREIGN KEY (documentlink_id) REFERENCES public.documentlink(id);


--
-- Name: pathdataiteration_documentlink fk_pathdataiteration_documentlink_pathdata_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration_documentlink
    ADD CONSTRAINT fk_pathdataiteration_documentlink_pathdata_iteration FOREIGN KEY (pathdata_iteration, pathdatamaster_id) REFERENCES public.pathdataiteration(iteration, pathdatamaster_id);


--
-- Name: pathdataiteration fk_pathdataiteration_pathdatamaster_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pathdataiteration
    ADD CONSTRAINT fk_pathdataiteration_pathdatamaster_id FOREIGN KEY (pathdatamaster_id) REFERENCES public.pathdatamaster(id);


--
-- Name: prdcfg_optionallink fk_prdcfg_optionallink_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdcfg_optionallink
    ADD CONSTRAINT fk_prdcfg_optionallink_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productconfiguration(id);


--
-- Name: prdcfg_substitutelink fk_prdcfg_substitutelink_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdcfg_substitutelink
    ADD CONSTRAINT fk_prdcfg_substitutelink_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productconfiguration(id);


--
-- Name: prdinstanceiteration_optlink fk_prdinstanceiteration_optlink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstanceiteration_optlink
    ADD CONSTRAINT fk_prdinstanceiteration_optlink_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstanceiteration_sublink fk_prdinstanceiteration_sublink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstanceiteration_sublink
    ADD CONSTRAINT fk_prdinstanceiteration_sublink_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstiteration_attribute fk_prdinstiteration_attribute_instanceattribute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_attribute
    ADD CONSTRAINT fk_prdinstiteration_attribute_instanceattribute_id FOREIGN KEY (instanceattribute_id) REFERENCES public.instanceattribute(id);


--
-- Name: prdinstiteration_attribute fk_prdinstiteration_attribute_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_attribute
    ADD CONSTRAINT fk_prdinstiteration_attribute_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstiteration_binres fk_prdinstiteration_binres_attachedfile_fullname; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_binres
    ADD CONSTRAINT fk_prdinstiteration_binres_attachedfile_fullname FOREIGN KEY (attachedfile_fullname) REFERENCES public.binaryresource(fullname);


--
-- Name: prdinstiteration_binres fk_prdinstiteration_binres_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_binres
    ADD CONSTRAINT fk_prdinstiteration_binres_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstiteration_documentlink fk_prdinstiteration_documentlink_documentlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_documentlink
    ADD CONSTRAINT fk_prdinstiteration_documentlink_documentlink_id FOREIGN KEY (documentlink_id) REFERENCES public.documentlink(id);


--
-- Name: prdinstiteration_documentlink fk_prdinstiteration_documentlink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_documentlink
    ADD CONSTRAINT fk_prdinstiteration_documentlink_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstiteration_p2plink fk_prdinstiteration_p2plink_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_p2plink
    ADD CONSTRAINT fk_prdinstiteration_p2plink_iteration FOREIGN KEY (iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: prdinstiteration_p2plink fk_prdinstiteration_p2plink_pathtopathlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_p2plink
    ADD CONSTRAINT fk_prdinstiteration_p2plink_pathtopathlink_id FOREIGN KEY (pathtopathlink_id) REFERENCES public.pathtopathlink(id);


--
-- Name: prdinstiteration_pathdatamstr fk_prdinstiteration_pathdatamstr_pathdatamaster_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_pathdatamstr
    ADD CONSTRAINT fk_prdinstiteration_pathdatamstr_pathdatamaster_id FOREIGN KEY (pathdatamaster_id) REFERENCES public.pathdatamaster(id);


--
-- Name: prdinstiteration_pathdatamstr fk_prdinstiteration_pathdatamstr_prdinstanceiteration_iteration; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prdinstiteration_pathdatamstr
    ADD CONSTRAINT fk_prdinstiteration_pathdatamstr_prdinstanceiteration_iteration FOREIGN KEY (prdinstanceiteration_iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id) REFERENCES public.productinstanceiteration(iteration, workspace_id, prdinstancemaster_serialnumber, configurationitem_id);


--
-- Name: productbaseline fk_productbaseline_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline
    ADD CONSTRAINT fk_productbaseline_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: productbaseline fk_productbaseline_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline
    ADD CONSTRAINT fk_productbaseline_configurationitem_id FOREIGN KEY (configurationitem_id, configurationitem_workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: productbaseline fk_productbaseline_documentcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline
    ADD CONSTRAINT fk_productbaseline_documentcollection_id FOREIGN KEY (documentcollection_id) REFERENCES public.documentcollection(id);


--
-- Name: productbaseline_optionallink fk_productbaseline_optionallink_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline_optionallink
    ADD CONSTRAINT fk_productbaseline_optionallink_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productbaseline(id);


--
-- Name: productbaseline_p2plink fk_productbaseline_p2plink_pathtopathlink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline_p2plink
    ADD CONSTRAINT fk_productbaseline_p2plink_pathtopathlink_id FOREIGN KEY (pathtopathlink_id) REFERENCES public.pathtopathlink(id);


--
-- Name: productbaseline_p2plink fk_productbaseline_p2plink_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline_p2plink
    ADD CONSTRAINT fk_productbaseline_p2plink_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productbaseline(id);


--
-- Name: productbaseline fk_productbaseline_partcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline
    ADD CONSTRAINT fk_productbaseline_partcollection_id FOREIGN KEY (partcollection_id) REFERENCES public.partcollection(id);


--
-- Name: productbaseline_substitutelink fk_productbaseline_substitutelink_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productbaseline_substitutelink
    ADD CONSTRAINT fk_productbaseline_substitutelink_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productbaseline(id);


--
-- Name: productconfiguration fk_productconfiguration_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productconfiguration
    ADD CONSTRAINT fk_productconfiguration_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: productconfiguration fk_productconfiguration_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productconfiguration
    ADD CONSTRAINT fk_productconfiguration_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: productconfiguration fk_productconfiguration_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productconfiguration
    ADD CONSTRAINT fk_productconfiguration_configurationitem_id FOREIGN KEY (configurationitem_id, configurationitem_workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: productinstanceiteration fk_productinstanceiteration_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT fk_productinstanceiteration_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: productinstanceiteration fk_productinstanceiteration_documentcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT fk_productinstanceiteration_documentcollection_id FOREIGN KEY (documentcollection_id) REFERENCES public.documentcollection(id);


--
-- Name: productinstanceiteration fk_productinstanceiteration_partcollection_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT fk_productinstanceiteration_partcollection_id FOREIGN KEY (partcollection_id) REFERENCES public.partcollection(id);


--
-- Name: productinstanceiteration fk_productinstanceiteration_prdinstancemaster_serialnumber; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT fk_productinstanceiteration_prdinstancemaster_serialnumber FOREIGN KEY (prdinstancemaster_serialnumber, workspace_id, configurationitem_id) REFERENCES public.productinstancemaster(serialnumber, workspace_id, configurationitem_id);


--
-- Name: productinstanceiteration fk_productinstanceiteration_productbaseline_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstanceiteration
    ADD CONSTRAINT fk_productinstanceiteration_productbaseline_id FOREIGN KEY (productbaseline_id) REFERENCES public.productbaseline(id);


--
-- Name: productinstancemaster fk_productinstancemaster_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstancemaster
    ADD CONSTRAINT fk_productinstancemaster_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: productinstancemaster fk_productinstancemaster_configurationitem_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.productinstancemaster
    ADD CONSTRAINT fk_productinstancemaster_configurationitem_id FOREIGN KEY (configurationitem_id, workspace_id) REFERENCES public.configurationitem(id, workspace_id);


--
-- Name: providedaccount fk_providedaccount_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.providedaccount
    ADD CONSTRAINT fk_providedaccount_id FOREIGN KEY (id) REFERENCES public.oauthprovider(id);


--
-- Name: providedaccount fk_providedaccount_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.providedaccount
    ADD CONSTRAINT fk_providedaccount_login FOREIGN KEY (login) REFERENCES public.account(login);


--
-- Name: pusagelink_psubstitutelink fk_pusagelink_psubstitutelink_partsubstitute_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pusagelink_psubstitutelink
    ADD CONSTRAINT fk_pusagelink_psubstitutelink_partsubstitute_id FOREIGN KEY (partsubstitute_id) REFERENCES public.partsubstitutelink(id);


--
-- Name: pusagelink_psubstitutelink fk_pusagelink_psubstitutelink_partusagelink_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pusagelink_psubstitutelink
    ADD CONSTRAINT fk_pusagelink_psubstitutelink_partusagelink_id FOREIGN KEY (partusagelink_id) REFERENCES public.partusagelink(id);


--
-- Name: query fk_query_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query
    ADD CONSTRAINT fk_query_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: query_grouped_by fk_query_grouped_by_query_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query_grouped_by
    ADD CONSTRAINT fk_query_grouped_by_query_id FOREIGN KEY (query_id) REFERENCES public.query(id);


--
-- Name: query_order_by fk_query_order_by_query_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query_order_by
    ADD CONSTRAINT fk_query_order_by_query_id FOREIGN KEY (query_id) REFERENCES public.query(id);


--
-- Name: query fk_query_pathdata_queryrule_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query
    ADD CONSTRAINT fk_query_pathdata_queryrule_id FOREIGN KEY (pathdata_queryrule_id) REFERENCES public.queryrule(qid);


--
-- Name: query fk_query_queryrule_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query
    ADD CONSTRAINT fk_query_queryrule_id FOREIGN KEY (queryrule_id) REFERENCES public.queryrule(qid);


--
-- Name: query_selects fk_query_selects_query_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.query_selects
    ADD CONSTRAINT fk_query_selects_query_id FOREIGN KEY (query_id) REFERENCES public.query(id);


--
-- Name: querycontext fk_querycontext_query_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.querycontext
    ADD CONSTRAINT fk_querycontext_query_id FOREIGN KEY (query_id) REFERENCES public.query(id);


--
-- Name: queryrule fk_queryrule_parent_query_rule; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queryrule
    ADD CONSTRAINT fk_queryrule_parent_query_rule FOREIGN KEY (parent_query_rule) REFERENCES public.queryrule(qid);


--
-- Name: queryrule_values fk_queryrule_values_queryrule_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.queryrule_values
    ADD CONSTRAINT fk_queryrule_values_queryrule_id FOREIGN KEY (queryrule_id) REFERENCES public.queryrule(qid);


--
-- Name: role_user fk_role_user_role_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_user
    ADD CONSTRAINT fk_role_user_role_name FOREIGN KEY (role_name, role_workspace_id) REFERENCES public.role(name, workspace_id);


--
-- Name: role_user fk_role_user_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_user
    ADD CONSTRAINT fk_role_user_user_login FOREIGN KEY (user_login, user_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: role_usergroup fk_role_usergroup_role_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_usergroup
    ADD CONSTRAINT fk_role_usergroup_role_name FOREIGN KEY (role_name, role_workspace_id) REFERENCES public.role(name, workspace_id);


--
-- Name: role_usergroup fk_role_usergroup_usergroup_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role_usergroup
    ADD CONSTRAINT fk_role_usergroup_usergroup_id FOREIGN KEY (usergroup_id, usergroup_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: role fk_role_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT fk_role_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: sharedentity fk_sharedentity_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharedentity
    ADD CONSTRAINT fk_sharedentity_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: sharedentity fk_sharedentity_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharedentity
    ADD CONSTRAINT fk_sharedentity_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, entity_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: sharedentity fk_sharedentity_partrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharedentity
    ADD CONSTRAINT fk_sharedentity_partrevision_version FOREIGN KEY (partrevision_version, partmaster_partnumber, entity_workspace_id) REFERENCES public.partrevision(version, partmaster_partnumber, workspace_id);


--
-- Name: sharedentity fk_sharedentity_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sharedentity
    ADD CONSTRAINT fk_sharedentity_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: statechangesubscription fk_statechangesubscription_documentrevision_version; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statechangesubscription
    ADD CONSTRAINT fk_statechangesubscription_documentrevision_version FOREIGN KEY (documentrevision_version, documentmaster_id, documentmaster_workspace_id) REFERENCES public.documentrevision(version, documentmaster_id, workspace_id);


--
-- Name: statechangesubscription fk_statechangesubscription_subscriber_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.statechangesubscription
    ADD CONSTRAINT fk_statechangesubscription_subscriber_login FOREIGN KEY (subscriber_login, subscriber_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: tag fk_tag_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tag
    ADD CONSTRAINT fk_tag_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: tagusergroupsubscription fk_tagusergroupsubscription_subscriber_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusergroupsubscription
    ADD CONSTRAINT fk_tagusergroupsubscription_subscriber_id FOREIGN KEY (subscriber_id, subscriber_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: tagusergroupsubscription fk_tagusergroupsubscription_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusergroupsubscription
    ADD CONSTRAINT fk_tagusergroupsubscription_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: tagusersubscription fk_tagusersubscription_subscriber_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusersubscription
    ADD CONSTRAINT fk_tagusersubscription_subscriber_login FOREIGN KEY (subscriber_login, subscriber_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: tagusersubscription fk_tagusersubscription_tag_label; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tagusersubscription
    ADD CONSTRAINT fk_tagusersubscription_tag_label FOREIGN KEY (tag_label, tag_workspace_id) REFERENCES public.tag(label, workspace_id);


--
-- Name: task fk_task_activity_step; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_activity_step FOREIGN KEY (activity_step, workflow_id) REFERENCES public.activity(step, workflow_id);


--
-- Name: task_user fk_task_user_task_num; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_user
    ADD CONSTRAINT fk_task_user_task_num FOREIGN KEY (task_num, activity_step, workflow_id) REFERENCES public.task(num, activity_step, workflow_id);


--
-- Name: task_user fk_task_user_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_user
    ADD CONSTRAINT fk_task_user_user_login FOREIGN KEY (user_login, user_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: task_usergroup fk_task_usergroup_task_num; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_usergroup
    ADD CONSTRAINT fk_task_usergroup_task_num FOREIGN KEY (task_num, activity_step, workflow_id) REFERENCES public.task(num, activity_step, workflow_id);


--
-- Name: task_usergroup fk_task_usergroup_usergroup_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_usergroup
    ADD CONSTRAINT fk_task_usergroup_usergroup_id FOREIGN KEY (usergroup_id, usergroup_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: task fk_task_worker_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_worker_login FOREIGN KEY (worker_login, worker_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: taskmodel fk_taskmodel_activitymodel_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taskmodel
    ADD CONSTRAINT fk_taskmodel_activitymodel_id FOREIGN KEY (activitymodel_id) REFERENCES public.activitymodel(id);


--
-- Name: taskmodel fk_taskmodel_role_name; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.taskmodel
    ADD CONSTRAINT fk_taskmodel_role_name FOREIGN KEY (role_name, role_workspace_id) REFERENCES public.role(name, workspace_id);


--
-- Name: userdata fk_userdata_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.userdata
    ADD CONSTRAINT fk_userdata_login FOREIGN KEY (login) REFERENCES public.account(login);


--
-- Name: userdata fk_userdata_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.userdata
    ADD CONSTRAINT fk_userdata_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: usergroup_user fk_usergroup_user_user_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroup_user
    ADD CONSTRAINT fk_usergroup_user_user_login FOREIGN KEY (user_login, user_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: usergroup_user fk_usergroup_user_usergroup_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroup_user
    ADD CONSTRAINT fk_usergroup_user_usergroup_id FOREIGN KEY (usergroup_id, usergroup_id_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: usergroup fk_usergroup_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usergroup
    ADD CONSTRAINT fk_usergroup_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: webhook fk_webhook_webhookapp_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT fk_webhook_webhookapp_id FOREIGN KEY (webhookapp_id) REFERENCES public.webhookapp(id);


--
-- Name: webhook fk_webhook_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook
    ADD CONSTRAINT fk_webhook_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workflowmodel fk_workflowmodel_acl_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflowmodel
    ADD CONSTRAINT fk_workflowmodel_acl_id FOREIGN KEY (acl_id) REFERENCES public.acl(id);


--
-- Name: workflowmodel fk_workflowmodel_author_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflowmodel
    ADD CONSTRAINT fk_workflowmodel_author_login FOREIGN KEY (author_login, author_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: workflowmodel fk_workflowmodel_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workflowmodel
    ADD CONSTRAINT fk_workflowmodel_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workspace_aborted_workflow fk_workspace_aborted_workflow_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_aborted_workflow
    ADD CONSTRAINT fk_workspace_aborted_workflow_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: workspace_aborted_workflow fk_workspace_aborted_workflow_workspace_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_aborted_workflow
    ADD CONSTRAINT fk_workspace_aborted_workflow_workspace_workflow_id FOREIGN KEY (workspace_workflow_id, workspace_workflow_workspace_id) REFERENCES public.workspace_workflow(id, workspace_id);


--
-- Name: workspace fk_workspace_admin_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace
    ADD CONSTRAINT fk_workspace_admin_login FOREIGN KEY (admin_login) REFERENCES public.account(login);


--
-- Name: workspace_documenttablecolumn fk_workspace_documenttablecolumn_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_documenttablecolumn
    ADD CONSTRAINT fk_workspace_documenttablecolumn_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspacefrontoptions(workspace_id);


--
-- Name: workspace_parttablecolumn fk_workspace_parttablecolumn_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_parttablecolumn
    ADD CONSTRAINT fk_workspace_parttablecolumn_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspacefrontoptions(workspace_id);


--
-- Name: workspace_workflow fk_workspace_workflow_workflow_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_workflow
    ADD CONSTRAINT fk_workspace_workflow_workflow_id FOREIGN KEY (workflow_id) REFERENCES public.workflow(id);


--
-- Name: workspace_workflow fk_workspace_workflow_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspace_workflow
    ADD CONSTRAINT fk_workspace_workflow_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workspacebackoptions fk_workspacebackoptions_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacebackoptions
    ADD CONSTRAINT fk_workspacebackoptions_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workspacefrontoptions fk_workspacefrontoptions_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspacefrontoptions
    ADD CONSTRAINT fk_workspacefrontoptions_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workspaceusergroupmembership fk_workspaceusergroupmembership_member_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusergroupmembership
    ADD CONSTRAINT fk_workspaceusergroupmembership_member_id FOREIGN KEY (member_id, member_workspace_id) REFERENCES public.usergroup(id, workspace_id);


--
-- Name: workspaceusergroupmembership fk_workspaceusergroupmembership_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusergroupmembership
    ADD CONSTRAINT fk_workspaceusergroupmembership_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- Name: workspaceusermembership fk_workspaceusermembership_member_login; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusermembership
    ADD CONSTRAINT fk_workspaceusermembership_member_login FOREIGN KEY (member_login, member_workspace_id) REFERENCES public.userdata(login, workspace_id);


--
-- Name: workspaceusermembership fk_workspaceusermembership_workspace_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.workspaceusermembership
    ADD CONSTRAINT fk_workspaceusermembership_workspace_id FOREIGN KEY (workspace_id) REFERENCES public.workspace(id);


--
-- PostgreSQL database dump complete
--

