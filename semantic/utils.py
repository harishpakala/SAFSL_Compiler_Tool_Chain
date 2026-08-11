'''
Created on Aug 10, 2026

@author: haris

Shared utilities for AAS -> RDF/OWL/SHACL lifting.
'''

import base64
import hashlib
import json

import requests

from rdflib import (
    Graph,
    Namespace,
    URIRef,
    Literal,
)

from rdflib.namespace import (
    RDF,
    RDFS,
    XSD,
    OWL,
)

import aas_core3_1.jsonization as aas_jsonization


# =============================================================================
# CONFIGURATION
# =============================================================================

BASE_URI = "http://org.example.com"

GRAPHDB_REPOSITORY = "AAS"

GRAPHDB_QUERY_ENDPOINT = (
    f"http://localhost:7200/repositories/{GRAPHDB_REPOSITORY}"
)

GRAPHDB_UPDATE_ENDPOINT = (
    f"http://localhost:7200/repositories/"
    f"{GRAPHDB_REPOSITORY}/statements"
)


# =============================================================================
# NAMESPACES
# =============================================================================

semanticDict = {}

semanticDict["AAS"] = Namespace(
    "https://example.org/aas/"
)

semanticDict["ECAD"] = Namespace(
    "https://example.org/ecad/"
)

semanticDict["DEXPI"] = Namespace(
    "https://example.org/dexpi/"
)

semanticDict["EX"] = Namespace(
    "http://example.org/ex#"
)

semanticDict["ECLASS"] = Namespace(
    "http://example.org/eclass#"
)

semanticDict["SH"] = Namespace(
    "http://www.w3.org/ns/shacl#"
)

semanticDict["QUDT"] = Namespace(
    "http://qudt.org/schema/qudt/"
)

semanticDict["UNIT"] = Namespace(
    "http://qudt.org/vocab/unit/"
)


# =============================================================================
# CARDINALITY
# =============================================================================

CARDINALITY = {
    "ZeroToOne": (0, 1),
    "One": (1, 1),
    "ZeroToMany": (0, None),
    "OneToMany": (1, None),
}


# =============================================================================
# HASH / URI UTILITIES
# =============================================================================

def sha256(value: str) -> str:
    """
    SHA256 hash of a string.
    """

    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def b64(value: str) -> str:
    """
    URL-friendly-ish base64 without padding.

    This follows the URI generation approach used
    in the original implementation.
    """

    return base64.b64encode(
        value.encode("utf-8")
    ).decode("utf-8").rstrip("=")


def compute_uri(
    submodel_id: str,
    path: str = "",
) -> URIRef:
    """
    Compute the URI for a template or instance resource.

    Root:

        compute_uri(submodel_id, "")

    Child:

        compute_uri(submodel_id, "Equipments")

    Nested:

        compute_uri(
            submodel_id,
            "Equipments.K-001"
        )
    """

    sub_hash = b64(submodel_id)

    path_hash = b64(
        path if path else ""
    )

    return URIRef(
        f"{BASE_URI}/{sub_hash}/{path_hash}"
    )


def predicate_from_idshort(
    id_short: str,
) -> URIRef:
    """
    Legacy/general predicate generation.

    Template lifting normally uses compute_uri()
    because template paths must remain stable.
    """

    if not id_short:
        raise ValueError(
            "id_short cannot be empty."
        )

    return URIRef(
        BASE_URI
        + "/has"
        + id_short[0].upper()
        + id_short[1:]
    )


def predicate_for_relation(
    id_short: str,
) -> URIRef:
    """
    Predicate for RelationshipElement.
    """

    return URIRef(
        BASE_URI
        + "/"
        + id_short
    )


# =============================================================================
# DATATYPE
# =============================================================================

def map_xsd_datatype(
    value_type: str,
):
    """
    Map AAS valueType to XSD datatype.

    Examples:

        xs:string   -> xsd:string
        xs:boolean  -> xsd:boolean
        xs:int      -> xsd:integer
        xs:integer  -> xsd:integer
        xs:float    -> xsd:float
        xs:double   -> xsd:double
        xs:decimal  -> xsd:decimal
    """

    if value_type is None:
        return XSD.string

    value_type = str(
        value_type
    ).strip()

    # Handle strings such as:
    #
    # xs:string
    # xsd:string
    # string

    value_type = (
        value_type
        .replace("xs:", "")
        .replace("xsd:", "")
        .lower()
    )

    mapping = {
        "string": XSD.string,

        "boolean": XSD.boolean,

        "int": XSD.integer,
        "integer": XSD.integer,

        "long": XSD.long,

        "short": XSD.short,

        "byte": XSD.byte,

        "unsignedint": XSD.unsignedInt,
        "unsignedlong": XSD.unsignedLong,

        "float": XSD.float,
        "double": XSD.double,

        "decimal": XSD.decimal,

        "date": XSD.date,
        "datetime": XSD.dateTime,
        "dateTime": XSD.dateTime,

        "time": XSD.time,
    }

    return mapping.get(
        value_type,
        XSD.string,
    )


# =============================================================================
# QUALIFIERS
# =============================================================================

def get_qualifier(
    element,
    qualifier_type: str,
):
    """
    Return the first qualifier with the requested type.
    """

    if not getattr(
        element,
        "qualifiers",
        None,
    ):
        return None

    for qualifier in element.qualifiers:

        if qualifier.type == qualifier_type:
            return qualifier

    return None


def get_cardinality(
    element,
):
    """
    Read the AAS template Cardinality qualifier.

    Returns:

        (min_count, max_count)

    Examples:

        One          -> (1, 1)
        ZeroToOne    -> (0, 1)
        ZeroToMany   -> (0, None)
        OneToMany    -> (1, None)

    If no cardinality qualifier is present, return:

        (0, 1)

    This default is conservative for an optional single-valued
    element, but templates should ideally specify cardinality.
    """

    qualifier = get_qualifier(
        element,
        "Cardinality",
    )

    if qualifier is None:
        return 0, 1

    value = qualifier.value

    if value not in CARDINALITY:

        raise ValueError(
            f"Unsupported cardinality '{value}' "
            f"on element '{element.id_short}'. "
            f"Supported values: "
            f"{list(CARDINALITY.keys())}"
        )

    return CARDINALITY[value]


def get_onto_concept(
    element,
):
    """
    Return ontoConcept qualifier value if present.
    """

    qualifier = get_qualifier(
        element,
        "ontoConcept",
    )

    if qualifier is None:
        return None

    return qualifier.value


# =============================================================================
# SEMANTIC ID
# =============================================================================

def resolve_semantic_id(
    uri: URIRef,
) -> str:
    """
    Resolve SemanticId into one of the supported modes.
    """

    uri = str(uri)

    if uri.startswith(
        "http://qudt.org/vocab/unit/"
    ):
        return "unit"

    if uri.startswith(
        "http://qudt.org/vocab/quantitykind/"
    ):
        return "quantitykind"

    if uri.startswith(
        "https://eclass.eu/"
    ):
        return "classification"

    return "annotation"


def lift_semantic_id(
    graph: Graph,
    submodel_id: str,
    element,
    path: str,
):
    """
    Add semantic-id information to the lifted resource.
    """

    semantic_id = getattr(
        element,
        "semantic_id",
        None,
    )

    if semantic_id is None:
        return

    if len(semantic_id.keys) == 0:
        return

    semantic_uri = URIRef(
        semantic_id.keys[-1].value
    )

    element_uri = compute_uri(
        submodel_id,
        path,
    )

    mode = resolve_semantic_id(
        semantic_uri
    )

    if mode == "unit":

        graph.add(
            (
                element_uri,
                semanticDict["QUDT"].hasUnit,
                semantic_uri,
            )
        )

    elif mode == "quantitykind":

        graph.add(
            (
                element_uri,
                semanticDict["QUDT"].hasQuantityKind,
                semantic_uri,
            )
        )

    elif mode == "classification":

        graph.add(
            (
                element_uri,
                RDF.type,
                semantic_uri,
            )
        )

    else:

        graph.add(
            (
                element_uri,
                RDFS.seeAlso,
                semantic_uri,
            )
        )


# =============================================================================
# GRAPH CREATION
# =============================================================================

def create_graph(
    submodel_id: str,
    domain: str,
) -> Graph:
    """
    Create an RDF graph with useful namespace bindings.
    """

    graph = Graph()

    graph.bind(
        "aas",
        semanticDict["AAS"],
    )

    graph.bind(
        "sh",
        semanticDict["SH"],
    )

    graph.bind(
        "owl",
        OWL,
    )

    graph.bind(
        "rdfs",
        RDFS,
    )

    graph.bind(
        "xsd",
        XSD,
    )

    graph.bind(
        "qudt",
        semanticDict["QUDT"],
    )

    graph.bind(
        "unit",
        semanticDict["UNIT"],
    )

    domain_upper = domain.upper()

    if domain_upper in semanticDict:

        graph.bind(
            domain,
            semanticDict[domain_upper],
        )

    return graph


# =============================================================================
# AAS JSON
# =============================================================================

def load_submodel(
    filename: str,
):
    """
    Load an AAS Submodel JSON file.
    """

    with open(
        filename,
        "r",
        encoding="utf-8",
    ) as f:

        model = json.load(f)

    return aas_jsonization.submodel_from_jsonable(
        model
    )


# =============================================================================
# GRAPHDB - PUSH
# =============================================================================

def push_to_graphdb(
    graph: Graph,
    submodel_id: str,
):
    """
    Push an RDF graph into a GraphDB named graph.

    Named graph:

        compute_uri(submodel_id)
    """

    graph_uri = compute_uri(
        submodel_id
    )

    # N-Triples is safer inside SPARQL INSERT DATA
    sparql_data = graph.serialize(
        format="nt"
    )

    query = f"""
    INSERT DATA {{
        GRAPH <{graph_uri}> {{
            {sparql_data}
        }}
    }}
    """

    response = requests.post(
        GRAPHDB_UPDATE_ENDPOINT,
        data=query.encode("utf-8"),
        headers={
            "Content-Type":
                "application/sparql-update"
        },
    )

    if response.status_code not in (
        200,
        204,
    ):

        raise RuntimeError(
            "Failed to insert graph into GraphDB.\n"
            f"HTTP status: {response.status_code}\n"
            f"{response.text}"
        )

    print(
        "Graph successfully pushed to GraphDB."
    )

    print(
        f"Named graph: {graph_uri}"
    )


# =============================================================================
# GRAPHDB - FETCH
# =============================================================================

def fetch_named_graph(
    graph_uri: URIRef,
) -> Graph:
    """
    Fetch an entire named graph from GraphDB.
    """

    query = f"""
    CONSTRUCT {{
        ?s ?p ?o
    }}
    WHERE {{
        GRAPH <{graph_uri}> {{
            ?s ?p ?o
        }}
    }}
    """

    response = requests.post(
        GRAPHDB_QUERY_ENDPOINT,
        data=query.encode("utf-8"),
        headers={
            "Content-Type":
                "application/sparql-query",
            "Accept":
                "text/turtle",
        },
    )

    if response.status_code != 200:

        raise RuntimeError(
            "Failed to fetch graph from GraphDB.\n"
            f"HTTP status: {response.status_code}\n"
            f"{response.text}"
        )

    graph = Graph()

    graph.parse(
        data=response.text,
        format="turtle",
    )

    # Preserve namespace bindings
    for prefix, namespace in graph.namespaces():
        pass

    return graph
