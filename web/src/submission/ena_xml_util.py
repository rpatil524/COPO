# COPO python file created 22/09/2017 by fshaw
from xml.etree.ElementTree import Element, SubElement, Comment, tostring
from xml.dom import minidom
from dal.copo_da import Submission, DataFile, Profile, Sample, Source, Person
import datetime
import web.apps.web_copo.lookup.lookup as lkup
from django_tools.middlewares.ThreadLocal import get_current_user


def do_study_xml(sub_id):
    # get submission object from mongo
    sub = Submission().get_record(sub_id)
    # get datafile objects
    dfs = list()
    for d in sub["bundle"]:
        dfs.append(DataFile().get_record(d))
    df = dfs[0]
    # get profile object
    p = Profile().get_record(df["profile_id"])

    # Do STUDY_SET
    study_set = Element("STUDY_SET")
    study_set.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    study_set.set("xsi:noNamespaceSchemaLocation", "ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.study.xsd")

    # Do STUDY
    study = Element("STUDY")
    study.set("alias", str(sub["_id"]))
    study.set("center_name", df["description"]["attributes"]["study_type"]["study_analysis_center_name"])
    study_set.append(study)

    # Do DESCRIPTOR
    descriptor = Element("DESCRIPTOR")
    # create element, append to parent and add text
    SubElement(descriptor, "STUDY_TITLE").text = p["title"]
    study_type = Element("STUDY_TYPE")
    es = get_study_type_enumeration(df["description"]["attributes"]["study_type"]["study_type"])
    # es = df["description"]["attributes"]["study_type"]["study_type"]
    study_type.set("existing_study_type", es)
    descriptor.append(study_type)
    SubElement(descriptor, "STUDY_ABSTRACT").text = p["description"]
    study.append(descriptor)

    # Do STUDY_ATTRIBUTES
    study_attributes = Element("STUDY_ATTRIBUTES")
    # do attribute for date
    study_attribute = Element("STUDY_ATTRIBUTE")
    SubElement(study_attribute, "TAG").text = "Submission Date"
    SubElement(study_attribute, "VALUE").text = datetime.datetime.now().strftime('%Y-%m-%d')
    study_attributes.append(study_attribute)

    # here we can loop to add other STUDY_ATTRIBUTES

    study.append(study_attributes)

    return prettify(study_set)


def do_sample_xml(sub_id):
    sub = Submission().get_record(sub_id)
    dfs = list()
    for d in sub["bundle"]:
        dfs.append(DataFile().get_record(d))
    df = dfs[0]
    # p = Profile().get_record(df["profile_id"])
    sample_set = Element("SAMPLE_SET")
    sample_set.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    sample_set.set("xsi:noNamespaceSchemaLocation", "ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.sample.xsd")

    smp = get_sample(df)

    # iterate samples to create xml
    sample = Element("SAMPLE")
    sample_alias = get_sample_ref(df)
    sample.set("alias", sample_alias)
    sample.set("center_name", df["description"]["attributes"]["study_type"]["study_center_name"])
    sample_set.append(sample)

    sample_name = Element("SAMPLE_NAME")
    sample_title = Element("TITLE")
    sample_title.text = smp["name"]
    sample.append(sample_title)
    sample.append(sample_name)

    # get Source object for organism
    s = Source().get_record(smp["derivesFrom"][0])
    taxon_id = Element("TAXON_ID")
    # get integer portion of NCBI taxon id
    taxon_id_content = s["organism"]["termAccession"].split('_')[1]
    taxon_id.text = taxon_id_content
    sample_name.append(taxon_id)
    scientific_name = Element("SCIENTIFIC_NAME")
    scientific_name.text = s["organism"]["annotationValue"]
    sample_name.append(scientific_name)
    common_name = Element("COMMON_NAME")
    sample_name.append(common_name)
    sample.append(Element("DESCRIPTION"))

    # do attributes
    attributes = Element("SAMPLE_ATTRIBUTES")
    for c in smp["characteristics"]:
        ch = Element("SAMPLE_ATTRIBUTE")
        tag = Element("TAG")
        tag.text = c["category"]["annotationValue"]
        value = Element("VALUE")
        value.text = c["value"]["annotationValue"]
        unit = Element("UNIT")
        unit.text = c["unit"]["annotationValue"]
        ch.append(tag)
        ch.append(value)
        ch.append(unit)
        attributes.append(ch)
    for c in smp["factorValues"]:
        ch = Element("SAMPLE_ATTRIBUTE")
        tag = Element("TAG")
        tag.text = c["category"]["annotationValue"]
        value = Element("VALUE")
        value.text = c["value"]["annotationValue"]
        unit = Element("UNIT")
        unit.text = c["unit"]["annotationValue"]
        ch.append(tag)
        ch.append(value)
        ch.append(unit)
        attributes.append(ch)

    sample.append(attributes)

    return prettify(sample_set)


def do_analysis_xml(sub_id):
    sub = Submission().get_record(sub_id)
    dfs = list()
    for d in sub["bundle"]:
        dfs.append(DataFile().get_record(d))
    df = dfs[0]
    p = Profile().get_record(df["profile_id"])
    analysis_set = Element("ANALYSIS_SET")
    analysis = Element("ANALYSIS")
    alias = make_alias(sub)
    analysis.set("alias", alias + "_anaysis")
    center_name = df["description"]["attributes"]["study_type"]["study_analysis_center_name"]
    analysis.set("analysis_center", center_name)
    broker_name = df["description"]["attributes"]["study_type"]["study_broker"]
    analysis.set("broker_name", broker_name)
    analysis_date = df["description"]["attributes"]["study_type"]["study_analysis_date"]
    # ad = analysis_date.split('/')
    # d = datetime.date(int(ad[2]), int(ad[1]), int(ad[0]))
    # analysis.set("anlalysis_date", d)
    # analysis_set.append(analysis)

    title = Element("TITLE")
    title.text = df["description"]["attributes"]["study_type"]["study_title"]
    analysis.append(title)

    description = Element("DESCRIPTION")
    description.text = df["description"]["attributes"]["study_type"]["study_description"]
    analysis.append(description)

    study_ref = Element("STUDY_REF")
    study_ref.set("refname", str(sub["_id"]))
    analysis.append(study_ref)

    # TODO - Analysis is not required for annotation submissions....ENA documentation saying it is is not correct. Will remove these stages from the wizard at some point
    s_ref = get_sample_ref(df)
    sample_ref = Element("SAMPLE_REF")
    sample_ref.set("refname", s_ref)
    # analysis.append(sample_ref)

    analysis_type = Element("ANALYSIS_TYPE")
    SubElement(analysis_type, "SEQUENCE_ANNOTATION")
    analysis.append(analysis_type)

    files = Element("FILES")
    file = Element("FILE")
    filename = df["name"]
    file_hash = df["file_hash"]

    fqfn = str(sub_id) + '/' + get_current_user().username + '/' + filename

    file.set("filename", fqfn)
    file.set("filetype", "tab")
    file.set("checksum_method", "MD5")
    file.set("checksum", file_hash)
    file.set("unencrypted_checksum", file_hash)
    files.append(file)
    analysis.append(files)

    attrs = Element("ANALYSIS_ATTRIBUTES")
    for a in df["description"]["attributes"]["attach_study_samples"]["attributes"]:
        attr = Element("ANALYSIS_ATTRIBUTE")
        tag = Element("TAG")
        tag.text = a["name"]
        value = Element("VALUE")
        value.text = a["value"]
        attr.append(tag)
        attr.append(value)
        attrs.append(attr)

    analysis.append(attrs)

    return prettify(analysis)


def do_submission_xml(sub_id):
    sub = Submission().get_record(sub_id)
    dfs = list()
    for d in sub["bundle"]:
        dfs.append(DataFile().get_record(d))
    df = dfs[0]

    submission = Element("SUBMISSION")
    # get names of files in bundle and append here
    # do alias
    alias = make_alias(sub)
    submission.set("alias", alias + "_sub")
    submission.set("broker_name", df["description"]["attributes"]["study_type"]["study_broker"])
    submission.set("center_name", df["description"]["attributes"]["study_type"]["study_analysis_center_name"])
    submission_date = datetime.datetime.now().isoformat()
    submission.set("submission_date", submission_date)
    submission.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
    submission.set("xsi:noNamespaceSchemaLocation", "ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_5/SRA.submission.xsd")

    contacts = Element("CONTACTS")
    copo_contact = Element("CONTACT")
    copo_contact.set("inform_on_error", "support@copo.org")
    copo_contact.set("inform_on_status", "support@copo.org")
    copo_contact.set("name", "COPO Support")
    contacts.append(copo_contact)

    people = Person(sub["profile_id"]).get_people_for_profile()
    for p in people:
        c = Element("CONTACT")
        c.set("name", p["firstName"] + " " + p["lastName"])
        if [x for x in p["roles"] if x["annotationValue"] == "SRA Inform On Status"]:
            c.set("inform_on_status", p["email"])
        if [x for x in p["roles"] if x["annotationValue"] == "SRA Inform On Error"]:
            c.set("inform_on_error", p["email"])
        contacts.append(c)
    submission.append(contacts)

    actions = Element("ACTIONS")
    action = Element("ACTION")
    add = Element("ADD")
    add.set("schema", "analysis")
    add.set("source", "analysis.xml")
    action.append(add)
    actions.append(action)
    submission.append(actions)

    return prettify(submission)


def prettify(elem):
    # Return a pretty-printed XML string for the Element.
    rough_string = tostring(elem, "utf-8")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def make_alias(sub):
    bundle = sub['bundle']
    filenames = ""
    for b in bundle:
        file = DataFile().get_record(b)
        filenames = filenames + "-" + file['name']
    alias = str(sub["_id"]) + ':' + sub['repository'] + ":" + filenames
    return alias


def get_sample(df):
    # get sample from datafile
    s_id = df["description"]["attributes"]["attach_study_samples"]["sample_copo"]
    if s_id != "":
        smp = Sample().get_record(s_id)
    else:
        s_id = df["description"]["attributes"]["attach_study_samples"]["sample_ena"]
        # TODO - get sample metadata from ENA tools
    return smp


def get_sample_ref(df):
    smp = get_sample(df)
    return str(smp["_id"]) + ":sample:" + smp["name"]


def get_study_type_enumeration(value):
    li = lkup.DROP_DOWNS['STUDY_TYPES']
    for l in li:
        if l['value'] == value:
            return l["label"]
