'''
Created on Aug 10, 2026

@author: haris

AAS Instance Lifting

Transforms an AAS Submodel Instance into RDF instance data.
'''
"""
instance_lifting.py

Lifts an AAS Submodel instance into RDF and validates it
against the SHACL shapes extracted from the corresponding
template graph stored in GraphDB.

Template:
    https://example.org/sm/dexpi

Instance:
    https://example.org/sm/dexpi25
"""

import json
import base64
import hashlib
from typing import Optional

import requests
from rdflib import (
    Graph,
    Dataset,
    Namespace,
    URIRef,
    Literal,
    RDF,
    RDFS,
    XSD,
)
from pyshacl import validate

import aas_core3_1.types as aas_types
import aas_core3_1.jsonization as aas_jsonization


# ============================================================
# Namespaces
# ============================================================

semanticDict = {}

semanticDict["AAS"] = Namespace("https://example.org/aas/")
semanticDict["ECAD"] = Namespace("https://example.org/ecad/")
semanticDict["DEXPI"] = Namespace("https://example.org/dexpi/")
semanticDict["EX"] = Namespace("http://example.org/ex#")
semanticDict["ECLASS"] = Namespace("http://example.org/eclass#")
semanticDict["SH"] = Namespace("http://www.w3.org/ns/shacl#")
semanticDict["QUDT"] = Namespace("http://qudt.org/schema/qudt/")
semanticDict["UNIT"] = Namespace("http://qudt.org/vocab/unit/")


# ============================================================
# Configuration
# ============================================================

BASE_URI = "http://org.example.com"

GRAPHDB_QUERY_ENDPOINT = (
    "http://localhost:7200/repositories/AAS"
)

GRAPHDB_STATEMENTS_ENDPOINT = (
    "http://localhost:7200/repositories/AAS/statements"
)

GRAPHDB_QUERY_HEADERS = {
    "Accept": "application/sparql-results+json"
}

GRAPHDB_UPDATE_HEADERS = {
    "Content-Type": "application/sparql-update"
}


# ============================================================
# URI utilities
# ============================================================

def sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def b64(value: str) -> str:
    return (
        base64.b64encode(value.encode("utf-8"))
        .decode("utf-8")
        .rstrip("=")
    )


def compute_uri(submodel_id: str, path: str = "") -> URIRef:
    """
    Compute the RDF URI for an AAS submodel/path.

    Example:

        compute_uri(
            "https://example.org/sm/dexpi",
            "Equipments.K-001.AssetIdentifier"
        )
    """

    sub_hash = b64(submodel_id)
    path_hash = b64(path if path else "")

    return URIRef(
        f"{BASE_URI}/{sub_hash}/{path_hash}"
    )


def predicate_from_idshort(id_short: str) -> URIRef:
    return URIRef(
        BASE_URI
        + "/has"
        + id_short[0].upper()
        + id_short[1:]
    )


def predicate_for_relation(id_short: str) -> URIRef:
    return URIRef(
        BASE_URI + "/" + id_short
    )


# ============================================================
# AAS helpers
# ============================================================

def get_onto_concept(element):
    """
    Return the value of an ontoConcept qualifier.
    """

    if not element.qualifiers:
        return None

    for qualifier in element.qualifiers:

        if qualifier.type == "ontoConcept":
            return qualifier.value

    return None


def map_xsd_datatype(value_type):

    mapping = {
        "string": XSD.string,
        "boolean": XSD.boolean,
        "int": XSD.integer,
        "integer": XSD.integer,
        "float": XSD.float,
        "double": XSD.double,
        "decimal": XSD.decimal,
    }

    if value_type is None:
        return XSD.string

    value_type = str(value_type).lower()

    return mapping.get(
        value_type,
        XSD.string
    )


# ============================================================
# GraphDB
# ============================================================

def fetch_template_graph(template_submodel_id: str) -> Graph:
    """
    Fetch the complete template named graph from GraphDB.
    """

    graph_uri = compute_uri(template_submodel_id)

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
        data={
            "query": query
        },
        headers={
            "Accept": "text/turtle"
        },
    )

    if response.status_code != 200:
        raise RuntimeError(
            "Failed to fetch template graph from GraphDB.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    template_graph = Graph()

    template_graph.parse(
        data=response.text,
        format="turtle"
    )

    print(
        f"Fetched template graph: {graph_uri}"
    )

    print(
        f"Template triples: {len(template_graph)}"
    )

    return template_graph


# ============================================================
# SHACL extraction
# ============================================================

def extract_shacl_graph(template_graph: Graph) -> Graph:
    """
    Extract only SHACL-related triples from the template graph.

    The template graph contains both:

        - OWL classes/properties
        - SHACL NodeShapes
        - SHACL PropertyShapes

    Validation only needs the SHACL graph.

    We therefore construct a separate Graph containing:

        sh:NodeShape
        sh:PropertyShape
        sh:targetClass
        sh:property
        sh:path
        sh:minCount
        sh:maxCount
        sh:datatype
        sh:class
        sh:node
        sh:nodeKind
        sh:hasValue
        sh:in
        sh:pattern
        sh:minInclusive
        sh:maxInclusive

    together with all blank-node/property-shape
    relationships needed by SHACL.
    """

    SH = semanticDict["SH"]

    shacl_graph = Graph()

    # --------------------------------------------------------
    # Bind namespaces
    # --------------------------------------------------------

    shacl_graph.bind(
        "sh",
        SH
    )

    shacl_graph.bind(
        "aas",
        semanticDict["AAS"]
    )

    shacl_graph.bind(
        "qudt",
        semanticDict["QUDT"]
    )

    shacl_graph.bind(
        "unit",
        semanticDict["UNIT"]
    )

    # --------------------------------------------------------
    # Find NodeShapes
    # --------------------------------------------------------

    node_shapes = set(
        template_graph.subjects(
            RDF.type,
            SH.NodeShape
        )
    )

    print(
        f"Found {len(node_shapes)} SHACL NodeShape(s)"
    )

    # --------------------------------------------------------
    # Find PropertyShapes
    # --------------------------------------------------------

    property_shapes = set(
        template_graph.subjects(
            RDF.type,
            SH.PropertyShape
        )
    )

    print(
        f"Found {len(property_shapes)} SHACL PropertyShape(s)"
    )

    # --------------------------------------------------------
    # Collect SHACL nodes
    # --------------------------------------------------------

    shacl_nodes = (
        node_shapes
        | property_shapes
    )

    # --------------------------------------------------------
    # Copy all SHACL triples reachable from shapes
    # --------------------------------------------------------

    queue = list(shacl_nodes)
    visited = set()

    while queue:

        current = queue.pop()

        if current in visited:
            continue

        visited.add(current)

        for predicate, obj in template_graph.predicate_objects(
            current
        ):

            # Keep SHACL structural triples.
            if predicate.startswith(SH):

                shacl_graph.add(
                    (
                        current,
                        predicate,
                        obj
                    )
                )

                # Follow blank nodes / SHACL nodes.
                if obj not in visited:
                    queue.append(obj)

    # --------------------------------------------------------
    # Explicitly copy important SHACL triples
    #
    # This is useful because some SHACL properties point to
    # OWL/AAS resources outside the SHACL namespace.
    # --------------------------------------------------------

    important_predicates = {
        SH["targetClass"],
        SH["property"],
        SH["path"],
        SH["minCount"],
        SH["maxCount"],
        SH["datatype"],
        SH["class"],
        SH["node"],
        SH["nodeKind"],
        SH["hasValue"],
        SH["in"],
        SH["pattern"],
        SH["minInclusive"],
        SH["maxInclusive"],
        SH["minExclusive"],
        SH["maxExclusive"],
        SH["minLength"],
        SH["maxLength"],
        SH["languageIn"],
        SH["uniqueLang"],
        SH["equals"],
        SH["disjoint"],
        SH["lessThan"],
        SH["lessThanOrEquals"],
    }

    for node in list(visited):

        for predicate, obj in template_graph.predicate_objects(
            node
        ):

            if predicate in important_predicates:

                shacl_graph.add(
                    (
                        node,
                        predicate,
                        obj
                    )
                )

    print(
        f"Extracted SHACL triples: "
        f"{len(shacl_graph)}"
    )

    return shacl_graph


# ============================================================
# SHACL validation
# ============================================================

def validate_instance(
    data_graph: Graph,
    shacl_graph: Graph
):
    """
    Validate an instance RDF graph against SHACL.
    """

    print()
    print("========================================")
    print("SHACL VALIDATION")
    print("========================================")

    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shacl_graph,
        inference="rdfs",
        debug=False,
    )

    if conforms:

        print(
            "✓ Instance conforms to template."
        )

        return True

    print(
        "✗ Instance does NOT conform "
        "to template."
    )

    print()
    print(report_text)

    return False


# ============================================================
# Instance lifting
# ============================================================

def lift_elements(
    graph: Graph,
    submodel_id: str,
    submodel_elements,
    parent_path: str,
    domain: str,
):
    """
    Lift all supported AAS instance elements.
    """

    for element in submodel_elements:

        if isinstance(
            element,
            aas_types.Property
        ):

            lift_property(
                graph,
                submodel_id,
                element,
                parent_path,
            )

        elif isinstance(
            element,
            aas_types.Range
        ):

            lift_range(
                graph,
                submodel_id,
                element,
                parent_path,
            )

        elif isinstance(
            element,
            aas_types.SubmodelElementCollection
        ):

            lift_smc(
                graph,
                submodel_id,
                element,
                parent_path,
                domain,
            )

        elif isinstance(
            element,
            aas_types.RelationshipElement
        ):

            lift_relationship(
                graph,
                submodel_id,
                element,
                parent_path,
            )


def lift_smc(
    graph: Graph,
    submodel_id: str,
    smc_element,
    parent_path: str,
    domain: str,
):
    """
    Lift an instance SubmodelElementCollection.

    Example:

        Equipments
            K-001
                AssetIdentifier
                Address
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + smc_element.id_short
        )

    else:

        path = smc_element.id_short

    smc_uri = compute_uri(
        submodel_id,
        path
    )

    parent_node = compute_uri(
        submodel_id,
        parent_path
    )

    # --------------------------------------------------------
    # Instance type
    # --------------------------------------------------------

    graph.add(
        (
            smc_uri,
            RDF.type,
            semanticDict["AAS"].SMC
        )
    )

    graph.add(
        (
            smc_uri,
            RDFS.label,
            Literal(
                smc_element.id_short
            )
        )
    )

    # --------------------------------------------------------
    # OntoConcept
    # --------------------------------------------------------

    onto_concept = get_onto_concept(
        smc_element
    )

    if onto_concept:

        concept_uri = URIRef(
            f"{domain}:{onto_concept}"
        )

        graph.add(
            (
                concept_uri,
                RDF.type,
                semanticDict["AAS"].SMC
            )
        )

        graph.add(
            (
                concept_uri,
                RDFS.label,
                Literal(onto_concept)
            )
        )

        graph.add(
            (
                smc_uri,
                RDF.type,
                concept_uri
            )
        )

        predicate = predicate_from_idshort(
            onto_concept
        )

    else:

        predicate = predicate_from_idshort(
            smc_element.id_short
        )

    # --------------------------------------------------------
    # Parent -> child
    # --------------------------------------------------------

    graph.add(
        (
            parent_node,
            predicate,
            smc_uri
        )
    )

    # --------------------------------------------------------
    # Children
    # --------------------------------------------------------

    lift_elements(
        graph,
        submodel_id,
        smc_element.value,
        path,
        domain,
    )


def lift_property(
    graph: Graph,
    submodel_id: str,
    property_element,
    parent_path: str,
):
    """
    Lift an AAS Property instance.
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + property_element.id_short
        )

    else:

        path = property_element.id_short

    parent_node = compute_uri(
        submodel_id,
        parent_path
    )

    predicate = predicate_from_idshort(
        property_element.id_short
    )

    datatype = map_xsd_datatype(
        property_element.value_type
    )

    value = Literal(
        property_element.value,
        datatype=datatype
    )

    graph.add(
        (
            parent_node,
            predicate,
            value
        )
    )


def lift_range(
    graph: Graph,
    submodel_id: str,
    range_element,
    parent_path: str,
):
    """
    Lift an AAS Range instance.
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + range_element.id_short
        )

    else:

        path = range_element.id_short

    parent_node = compute_uri(
        submodel_id,
        parent_path
    )

    range_uri = compute_uri(
        submodel_id,
        path
        + ".interval"
    )

    predicate = predicate_from_idshort(
        range_element.id_short
    )

    graph.add(
        (
            parent_node,
            predicate,
            range_uri
        )
    )

    graph.add(
        (
            range_uri,
            RDF.type,
            semanticDict["AAS"].Interval
        )
    )

    datatype = map_xsd_datatype(
        range_element.value_type
    )

    if (
        hasattr(range_element, "min")
        and range_element.min is not None
    ):

        graph.add(
            (
                range_uri,
                semanticDict["AAS"].min,
                Literal(
                    range_element.min,
                    datatype=datatype
                )
            )
        )

    if (
        hasattr(range_element, "max")
        and range_element.max is not None
    ):

        graph.add(
            (
                range_uri,
                semanticDict["AAS"].max,
                Literal(
                    range_element.max,
                    datatype=datatype
                )
            )
        )


def lift_relationship(
    graph: Graph,
    submodel_id: str,
    relationship_element,
    parent_path: str,
):
    """
    Lift an AAS RelationshipElement instance.
    """

    first_keys = relationship_element.first.keys

    first_submodel = first_keys[0].value

    first_path = ".".join(
        key.value
        for key in first_keys[1:]
    )

    first_uri = compute_uri(
        first_submodel,
        first_path
    )

    second_keys = relationship_element.second.keys

    second_submodel = second_keys[0].value

    second_path = ".".join(
        key.value
        for key in second_keys[1:]
    )

    second_uri = compute_uri(
        second_submodel,
        second_path
    )

    predicate = predicate_for_relation(
        relationship_element.id_short
    )

    graph.add(
        (
            first_uri,
            predicate,
            second_uri
        )
    )


# ============================================================
# Main instance lifting function
# ============================================================

def lift_instance(
    aas_submodel,
    domain: str,
) -> Graph:
    """
    Lift one AAS instance into an RDF graph.
    """

    graph = Graph()

    graph.bind(
        "aas",
        semanticDict["AAS"]
    )

    graph.bind(
        "ex",
        semanticDict["EX"]
    )

    graph.bind(
        "qudt",
        semanticDict["QUDT"]
    )

    graph.bind(
        "unit",
        semanticDict["UNIT"]
    )

    # --------------------------------------------------------
    # Root instance
    # --------------------------------------------------------

    root = compute_uri(
        aas_submodel.id
    )

    graph.add(
        (
            root,
            RDF.type,
            semanticDict["AAS"].SubmodelInstance
        )
    )

    graph.add(
        (
            root,
            RDFS.label,
            Literal(
                aas_submodel.id_short
            )
        )
    )

    # --------------------------------------------------------
    # Interval class
    # --------------------------------------------------------

    graph.add(
        (
            semanticDict["AAS"].Interval,
            RDF.type,
            URIRef(
                "http://www.w3.org/2002/07/owl#Class"
            )
        )
    )

    graph.add(
        (
            semanticDict["AAS"].Interval,
            RDFS.label,
            Literal("Interval")
        )
    )

    # --------------------------------------------------------
    # Lift elements
    # --------------------------------------------------------

    lift_elements(
        graph,
        aas_submodel.id,
        aas_submodel.submodel_elements,
        "",
        domain,
    )

    return graph


# ============================================================
# Push instance graph
# ============================================================

def push_instance_graph(
    graph: Graph,
    submodel_id: str,
):
    """
    Push the validated instance graph
    into its own named graph.
    """

    graph_uri = compute_uri(
        submodel_id
    )

    nt_data = graph.serialize(
        format="nt"
    )

    query = f"""
    INSERT DATA {{
        GRAPH <{graph_uri}> {{
            {nt_data}
        }}
    }}
    """

    response = requests.post(
        GRAPHDB_STATEMENTS_ENDPOINT,
        data=query.encode("utf-8"),
        headers=GRAPHDB_UPDATE_HEADERS,
    )

    if response.status_code not in (
        200,
        204,
    ):

        raise RuntimeError(
            "Failed to insert instance graph "
            "into GraphDB.\n"
            f"Status: {response.status_code}\n"
            f"Response: {response.text}"
        )

    print()
    print(
        f"✓ Instance graph pushed to: "
        f"{graph_uri}"
    )


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    # --------------------------------------------------------
    # Files
    # --------------------------------------------------------

    INSTANCE_FILE = "sample_dexpi.json"

    # The template is deliberately identified separately
    # from the instance.
    TEMPLATE_ID = (
        "https://example.org/sm/dexpi"
    )

    DOMAIN = "DEXPI"

    # --------------------------------------------------------
    # Read instance
    # --------------------------------------------------------

    with open(
        INSTANCE_FILE,
        "r",
        encoding="utf-8",
    ) as f:

        model = json.load(f)

    instance_submodel = (
        aas_jsonization.submodel_from_jsonable(
            model
        )
    )

    print()
    print("========================================")
    print("DEXPI INSTANCE LIFTING")
    print("========================================")

    print(
        f"Instance ID: "
        f"{instance_submodel.id}"
    )

    # --------------------------------------------------------
    # 1. Fetch template graph
    # --------------------------------------------------------

    print()
    print(
        "Fetching DEXPI template from GraphDB..."
    )

    template_graph = fetch_template_graph(
        TEMPLATE_ID
    )

    # --------------------------------------------------------
    # 2. Extract SHACL
    # --------------------------------------------------------

    shacl_graph = extract_shacl_graph(
        template_graph
    )

    # Optional debugging output
    print()
    print(
        "========================================"
    )
    print("EXTRACTED SHACL")
    print(
        "========================================"
    )

    print(
        shacl_graph.serialize(
            format="turtle"
        )
    )

    # --------------------------------------------------------
    # 3. Lift instance
    # --------------------------------------------------------

    instance_graph = lift_instance(
        instance_submodel,
        DOMAIN,
    )

    print()
    print(
        "========================================"
    )
    print("INSTANCE RDF")
    print(
        "========================================"
    )

    print(
        instance_graph.serialize(
            format="turtle"
        )
    )

    # --------------------------------------------------------
    # 4. Validate instance against template
    # --------------------------------------------------------

    conforms = validate_instance(
        instance_graph,
        shacl_graph,
    )

    if not conforms:

        print()
        print(
            "Instance was NOT pushed to GraphDB "
            "because SHACL validation failed."
        )

        raise SystemExit(1)

    # --------------------------------------------------------
    # 5. Push only validated instance
    # --------------------------------------------------------

    push_instance_graph(
        instance_graph,
        instance_submodel.id,
    )

    print()
    print(
        "========================================"
    )
    print("DONE")
    print(
        "========================================"
    )