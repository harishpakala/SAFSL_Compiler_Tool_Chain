'''
Created on Aug 01, 2026

@author: haris

instance_lifting.py

Semantic lifting of an AAS instance into RDF.

Design:
- The AAS instance is converted into an RDF instance graph.
- The template submodel ID is used to locate the corresponding
  SHACL graph in GraphDB.
- SHACL shapes are fetched from GraphDB; no local template file
  is required.
- Instance semantic concepts determine domain classes/predicates.
- Properties are represented as direct RDF literals.
- Instance resource URIs remain deterministic Base64 URIs.
- Instance labels use the original idShort.
'''

import json
import requests

from rdflib import (
    Graph,
    URIRef,
    Literal,
    RDF,
    RDFS,
    OWL,
    Namespace,
)

from pyshacl import validate

import aas_core3_1.types as aas_types
import aas_core3_1.jsonization as aas_jsonization

from semantic.ontoutils import (
    semanticDict,
    compute_uri,
    build_path,
    make_literal,
    get_ontology_concept,
    bind_common_namespaces,
    lift_semantic_id,
    push_graph_to_graphdb,
    get_graphdb_repository_url,
)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SH = Namespace("http://www.w3.org/ns/shacl#")

VALIDATE_INSTANCE = True

INSTANCE_GRAPH_URI = None


# ---------------------------------------------------------------------------
# Semantic URI helpers
# ---------------------------------------------------------------------------

def make_semantic_predicate(
    domain: str,
    concept: str,
) -> URIRef:
    """
    Create a domain semantic predicate.

    Example:
        domain = "dexpi"
        concept = "AssetIdentifier"

    Result:
        https://example.org/dexpi/hasAssetIdentifier
    """

    domain_upper = domain.upper()

    if domain_upper not in semanticDict:
        raise ValueError(
            f"Unknown domain namespace: {domain}"
        )

    if not concept:
        raise ValueError(
            "Cannot create semantic predicate "
            "without a concept."
        )

    return URIRef(
        str(semanticDict[domain_upper])
        + "has"
        + concept
    )


def make_domain_class(
    domain: str,
    concept: str,
) -> URIRef:
    """
    Create a domain semantic class.

    Example:
        dexpi + Equipment
        -> https://example.org/dexpi/Equipment
    """

    domain_upper = domain.upper()

    if domain_upper not in semanticDict:
        raise ValueError(
            f"Unknown domain namespace: {domain}"
        )

    if not concept:
        raise ValueError(
            "Cannot create domain class "
            "without a concept."
        )

    return URIRef(
        str(semanticDict[domain_upper])
        + concept
    )


# ---------------------------------------------------------------------------
# RDF resource helpers
# ---------------------------------------------------------------------------

def add_resource_type(
    graph: Graph,
    resource_uri: URIRef,
    aas_class: URIRef,
    label: str,
):
    """
    Add rdf:type and rdfs:label to an RDF resource.
    """

    graph.add(
        (
            resource_uri,
            RDF.type,
            aas_class,
        )
    )

    graph.add(
        (
            resource_uri,
            RDFS.label,
            Literal(label),
        )
    )


# ---------------------------------------------------------------------------
# Semantic concept resolution
# ---------------------------------------------------------------------------

def resolve_instance_concept(element) -> str | None:
    """
    Resolve the ontology concept attached to an AAS element.
    """

    concept = get_ontology_concept(element)

    if concept:
        return str(concept)

    return None


def resolve_predicate_concept(element) -> str:
    """
    Resolve the semantic predicate concept.

    If no ontology concept exists, fall back to idShort.
    """

    concept = resolve_instance_concept(element)

    if concept:
        return concept

    if not element.id_short:
        raise ValueError(
            "Cannot resolve predicate concept "
            "without idShort."
        )

    return str(element.id_short)


# ---------------------------------------------------------------------------
# AAS element lifting
# ---------------------------------------------------------------------------

def lift_property(
    graph: Graph,
    instance_id: str,
    element,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    """
    Lift an AAS Property into RDF.
    """

    path = build_path(
        parent_path,
        element.id_short,
    )

    predicate = make_semantic_predicate(
        domain,
        element.id_short,
    )

    value = make_literal(
        element.value,
        element.value_type,
    )

    # Direct semantic property.
    graph.add(
        (
            parent_uri,
            predicate,
            value,
        )
    )

    # Represent the AAS Property itself as an RDF resource.
    property_uri = compute_uri(
        instance_id,
        path,
    )

    graph.add(
        (
            property_uri,
            RDF.type,
            semanticDict["AAS"]["Property"],
        )
    )

    graph.add(
        (
            property_uri,
            RDFS.label,
            Literal(element.id_short),
        )
    )

    graph.add(
        (
            property_uri,
            RDF.type,
            OWL.NamedIndividual,
        )
    )

    lift_semantic_id(
        graph,
        instance_id,
        element,
        path,
    )


def lift_range(
    graph: Graph,
    instance_id: str,
    element,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    """
    Lift an AAS Range into RDF.
    """

    path = build_path(
        parent_path,
        element.id_short,
    )

    predicate = make_semantic_predicate(
        domain,
        element.id_short,
    )

    range_uri = compute_uri(
        instance_id,
        path,
    )

    add_resource_type(
        graph,
        range_uri,
        semanticDict["AAS"]["Range"],
        element.id_short,
    )

    graph.add(
        (
            parent_uri,
            predicate,
            range_uri,
        )
    )

    lift_semantic_id(
        graph,
        instance_id,
        element,
        path,
    )


def resolve_model_reference(
    instance_id: str,
    reference,
) -> URIRef:
    """
    Resolve an AAS model reference to the deterministic
    RDF URI of the referenced instance element.
    """

    path_parts = []

    for key in reference.keys:

        key_type = key.type.value
        key_value = str(key.value)

        if key_type == "Submodel":
            continue

        path_parts.append(key_value)

    path = ".".join(path_parts)

    return compute_uri(
        instance_id,
        path,
    )


def lift_relationship(
    graph: Graph,
    instance_id: str,
    element,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    """
    Lift an AAS RelationshipElement into RDF.
    """

    first_uri = resolve_model_reference(
        instance_id,
        element.first,
    )

    second_uri = resolve_model_reference(
        instance_id,
        element.second,
    )

    predicate = URIRef(
        str(semanticDict[domain.upper()])
        + element.id_short
    )

    graph.add(
        (
            first_uri,
            predicate,
            second_uri,
        )
    )


def lift_smc(
    graph: Graph,
    instance_id: str,
    element,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    """
    Lift an AAS SubmodelElementCollection into RDF.
    """

    path = build_path(
        parent_path,
        element.id_short,
    )

    element_uri = compute_uri(
        instance_id,
        path,
    )

    concept = resolve_instance_concept(
        element
    )

    if concept:
        instance_class = make_domain_class(
            domain,
            concept,
        )

        graph.add(
            (
                element_uri,
                RDF.type,
                instance_class,
            )
        )

    graph.add(
        (
            element_uri,
            RDF.type,
            semanticDict["AAS"]["SMC"],
        )
    )

    graph.add(
        (
            element_uri,
            RDFS.label,
            Literal(element.id_short),
        )
    )

    predicate_concept = resolve_predicate_concept(
        element
    )

    predicate = make_semantic_predicate(
        domain,
        predicate_concept,
    )

    graph.add(
        (
            parent_uri,
            predicate,
            element_uri,
        )
    )

    lift_semantic_id(
        graph,
        instance_id,
        element,
        path,
    )

    lift_instance_elements(
        graph=graph,
        instance_id=instance_id,
        elements=element.value,
        parent_path=path,
        parent_uri=element_uri,
        domain=domain,
    )


def lift_instance_elements(
    graph: Graph,
    instance_id: str,
    elements,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    """
    Recursively lift supported AAS submodel elements.
    """

    for element in elements:

        if isinstance(
            element,
            aas_types.Property,
        ):

            lift_property(
                graph,
                instance_id,
                element,
                parent_path,
                parent_uri,
                domain,
            )

        elif isinstance(
            element,
            aas_types.Range,
        ):

            lift_range(
                graph,
                instance_id,
                element,
                parent_path,
                parent_uri,
                domain,
            )

        elif isinstance(
            element,
            aas_types.SubmodelElementCollection,
        ):

            lift_smc(
                graph,
                instance_id,
                element,
                parent_path,
                parent_uri,
                domain,
            )

        elif isinstance(
            element,
            aas_types.RelationshipElement,
        ):

            lift_relationship(
                graph,
                instance_id,
                element,
                parent_path,
                parent_uri,
                domain,
            )

        else:

            print(
                "Warning: unsupported AAS element: "
                f"{type(element).__name__}"
            )


# ---------------------------------------------------------------------------
# Submodel lifting
# ---------------------------------------------------------------------------

def lift_submodel_root(
    graph: Graph,
    submodel,
    domain: str,
    template_submodel_id: str,
):
    """
    Lift the AAS Submodel root.

    The instance receives:
      - aas:Submodel
      - the template submodel URI as its semantic/template class
    """

    instance_id = submodel.id

    root_uri = compute_uri(
        instance_id,
        "",
    )

    template_class = compute_uri(
        template_submodel_id,
        "",
    )

    add_resource_type(
        graph,
        root_uri,
        semanticDict["AAS"]["Submodel"],
        submodel.id_short,
    )

    graph.add(
        (
            root_uri,
            RDF.type,
            template_class,
        )
    )

    lift_instance_elements(
        graph=graph,
        instance_id=instance_id,
        elements=submodel.submodel_elements,
        parent_path="",
        parent_uri=root_uri,
        domain=domain,
    )

    return root_uri


def build_instance_graph(
    submodel,
    domain: str,
    template_submodel_id: str,
) -> Graph:
    """
    Build the RDF graph representing the AAS instance.
    """

    graph = Graph()

    bind_common_namespaces(
        graph,
        domain,
    )

    lift_submodel_root(
        graph,
        submodel,
        domain,
        template_submodel_id,
    )

    return graph


# ---------------------------------------------------------------------------
# SHACL template retrieval
# ---------------------------------------------------------------------------

def fetch_template_graph(
    template_submodel_id: str,
) -> Graph:
    """
    Fetch the SHACL template graph from GraphDB.

    The template submodel ID is converted into the same deterministic
    graph URI used when the template was stored in GraphDB.
    """

    repository_url = get_graphdb_repository_url()

    graph_uri = compute_uri(
        template_submodel_id
    )

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
        repository_url,
        data={
            "query": query,
        },
        headers={
            "Accept": "text/turtle",
        },
        timeout=30,
    )

    if response.status_code != 200:

        print(
            "GraphDB response:",
            response.text,
        )

        raise RuntimeError(
            "Failed to fetch SHACL template graph "
            f"from GraphDB. HTTP status: "
            f"{response.status_code}"
        )

    template_graph = Graph()

    template_graph.parse(
        data=response.text,
        format="turtle",
    )

    if len(template_graph) == 0:
        raise RuntimeError(
            "GraphDB returned an empty SHACL template graph "
            f"for template submodel ID: "
            f"{template_submodel_id}"
        )

    return template_graph


# ---------------------------------------------------------------------------
# SHACL validation
# ---------------------------------------------------------------------------

def validate_instance(
    instance_graph: Graph,
    template_graph: Graph,
    instance_root: URIRef,
):
    """
    Validate the complete instance graph against the SHACL graph
    retrieved from GraphDB.
    """

    try:

        conforms, report_graph, report_text = validate(
            instance_graph,
            shacl_graph=template_graph,
            inference="none",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            advanced=True,
            debug=False,
        )

    except TypeError:

        # Compatibility fallback for pySHACL versions where
        # some validation options are not available.
        conforms, report_graph, report_text = validate(
            instance_graph,
            shacl_graph=template_graph,
            inference="none",
            abort_on_first=False,
            allow_infos=False,
            allow_warnings=False,
            advanced=False,
            debug=False,
        )

    print()
    print("SHACL VALIDATION")
    print("================")
    print(report_text)

    if not conforms:

        raise ValueError(
            "AAS instance does not conform "
            "to the template SHACL shapes."
        )

    return conforms, report_graph, report_text


# ---------------------------------------------------------------------------
# AAS JSON loading
# ---------------------------------------------------------------------------

def load_submodel(
    filename: str,
):
    """
    Load an AAS Submodel from JSON.
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


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------

def main(
    domain: str,
    instance_file: str,
    template_submodel_id: str,
):
    """
    Lift, validate and store one AAS instance.
    """

    print()
    print("==========================================")
    print("AAS INSTANCE LIFTING")
    print("==========================================")

    # -------------------------------------------------------
    # Load AAS instance
    # -------------------------------------------------------

    instance = load_submodel(
        instance_file
    )

    print(
        f"Instance ID: {instance.id}"
    )

    print(
        f"Instance idShort: {instance.id_short}"
    )

    # -------------------------------------------------------
    # Build instance RDF graph
    # -------------------------------------------------------

    print()
    print("Building instance graph...")

    instance_graph = build_instance_graph(
        instance,
        domain,
        template_submodel_id,
    )

    print(
        f"Instance triples: {len(instance_graph)}"
    )
    
    print(
        instance_graph.serialize(
            format="turtle"
        )
    )
    
    print("===========================")
    
    # -------------------------------------------------------
    # Fetch SHACL template from GraphDB
    # -------------------------------------------------------

    if VALIDATE_INSTANCE:

        print()
        print(
            "Fetching SHACL template from GraphDB..."
        )

        template_graph = fetch_template_graph(
            template_submodel_id
        )

        print(
            f"SHACL template triples: "
            f"{len(template_graph)}"
        )

        # ---------------------------------------------------
        # Validate instance
        # ---------------------------------------------------

        instance_root = compute_uri(
            instance.id,
            "",
        )

        validate_instance(
            instance_graph,
            template_graph,
            instance_root,
        )

        print()
        print("SHACL validation successful.")

    # -------------------------------------------------------
    # Push instance graph to GraphDB
    # -------------------------------------------------------

    graph_uri = (
        INSTANCE_GRAPH_URI
        if INSTANCE_GRAPH_URI is not None
        else compute_uri(instance.id)
    )

    print()
    print(
        "Pushing instance graph to GraphDB..."
    )

    push_graph_to_graphdb(
        instance_graph,
        graph_uri,
    )

    print()
    print("==========================================")
    print("INSTANCE LIFTING COMPLETE")
    print("==========================================")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":

    instance_data = {
        "dexpi": (
            "sample_dexpi_instance.json",
            "https://example.org/sm/dexpi",
        ),
        "ecad": (
            "sample_ecad_instance.json",
            "https://example.org/sm/ecad",
        ),
    }

    for domain, (
        instance_file,
        template_submodel_id,
    ) in instance_data.items():

        main(
            domain,
            instance_file,
            template_submodel_id,
        )