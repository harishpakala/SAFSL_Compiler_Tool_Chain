'''
Created on Aug 01, 2026

@author: haris
template_lifting.py

Semantic lifting of an AAS Submodel Template into RDF.

The generated template graph contains:

- AAS structural classes
- Domain semantic predicates
- SHACL NodeShapes
- SHACL PropertyShapes
- Cardinality constraints
- SemanticId enrichment

ontoConcept is intentionally not interpreted on the template side.
It is handled during instance lifting.
'''

import json

from rdflib import (
    Graph,
    URIRef,
    Literal,
    RDF,
    RDFS,
    OWL,
)

import aas_core3_1.types as aas_types
from aas_core3_1.types import KeyTypes
import aas_core3_1.jsonization as aas_jsonization

from semantic.ontoutils import (
    semanticDict,
    compute_uri,
    build_path,
    map_xsd_datatype,
    get_cardinality,
    make_shape_label,
    make_node_shape_label,
    add_cardinality_constraints,
    lift_semantic_id,
    bind_common_namespaces,
    push_graph_to_graphdb,
)


def make_semantic_predicate(
    domain: str,
    id_short: str,
) -> URIRef:

    if not id_short:
        raise ValueError(
            "Cannot create semantic predicate from empty idShort."
        )

    domain_upper = domain.upper()

    if domain_upper not in semanticDict:
        raise ValueError(
            f"Unknown domain namespace: {domain}"
        )

    return URIRef(
        str(semanticDict[domain_upper])
        + "has"
        + id_short
    )


def ensure_aas_class(
    graph: Graph,
    class_name: str,
    label: str,
) -> URIRef:

    class_uri = semanticDict["AAS"][class_name]

    graph.add(
        (
            class_uri,
            RDF.type,
            OWL.Class,
        )
    )

    graph.add(
        (
            class_uri,
            RDFS.label,
            Literal(label),
        )
    )

    return class_uri


def lift_template(
    submodel,
    graph: Graph,
    domain: str,
):

    template_id = submodel.id

    template_class = compute_uri(
        template_id,
        "",
    )

    graph.add(
        (
            template_class,
            RDF.type,
            OWL.Class,
        )
    )

    graph.add(
        (
            template_class,
            RDFS.label,
            Literal(submodel.id_short),
        )
    )

    template_shape = compute_uri(
        template_id,
        "shape",
    )

    graph.add(
        (
            template_shape,
            RDF.type,
            semanticDict["SH"]["NodeShape"],
        )
    )

    graph.add(
        (
            template_shape,
            RDFS.label,
            Literal(
                make_node_shape_label(
                    submodel.id_short
                )
            ),
        )
    )

    graph.add(
        (
            template_shape,
            semanticDict["SH"]["targetClass"],
            template_class,
        )
    )

    lift_elements(
        graph=graph,
        template_id=template_id,
        elements=submodel.submodel_elements,
        parent_path="",
        parent_shape=template_shape,
        domain=domain,
    )


def lift_elements(
    graph: Graph,
    template_id: str,
    elements,
    parent_path: str,
    parent_shape: URIRef,
    domain: str,
):

    for element in elements:

        if isinstance(
            element,
            aas_types.Property,
        ):
            lift_property(
                graph,
                template_id,
                element,
                parent_path,
                parent_shape,
                domain,
            )

        elif isinstance(
            element,
            aas_types.Range,
        ):
            lift_range(
                graph,
                template_id,
                element,
                parent_path,
                parent_shape,
                domain,
            )

        elif isinstance(
            element,
            aas_types.SubmodelElementCollection,
        ):
            lift_smc(
                graph,
                template_id,
                element,
                parent_path,
                parent_shape,
                domain,
            )

        elif isinstance(
            element,
            aas_types.RelationshipElement,
        ):
            lift_relationship(
                graph,
                template_id,
                element,
                parent_path,
                parent_shape,
                domain,
            )

        else:
            print(
                "Warning: unsupported AAS element type: "
                f"{type(element).__name__}"
            )

def lift_property(
    graph: Graph,
    template_id: str,
    element,
    parent_path: str,
    parent_shape: URIRef,
    domain: str,
):
    path = build_path(
        parent_path,
        element.id_short,
    )

    property_uri = make_semantic_predicate(
        domain,
        element.id_short,
    )

    shape_uri = compute_uri(
        template_id,
        path + "/shape",
    )

    graph.add(
        (
            property_uri,
            RDF.type,
            OWL.DatatypeProperty,
        )
    )

    graph.add(
        (
            property_uri,
            RDFS.label,
            Literal(
                "has" + element.id_short
            ),
        )
    )

    graph.add(
        (
            shape_uri,
            RDF.type,
            semanticDict["SH"]["PropertyShape"],
        )
    )

    graph.add(
        (
            shape_uri,
            RDFS.label,
            Literal(
                make_shape_label(
                    element.id_short
                )
            ),
        )
    )

    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["path"],
            property_uri,
        )
    )

    min_count, max_count = get_cardinality(
        element
    )

    add_cardinality_constraints(
        graph,
        shape_uri,
        min_count,
        max_count,
    )

    lift_semantic_id(
        graph,
        template_id,
        element,
        path,
    )

    graph.add(
        (
            parent_shape,
            semanticDict["SH"]["property"],
            shape_uri,
        )
    )

def lift_range(
    graph: Graph,
    template_id: str,
    element,
    parent_path: str,
    parent_shape: URIRef,
    domain: str,
):

    path = build_path(
        parent_path,
        element.id_short,
    )

    property_uri = make_semantic_predicate(
        domain,
        element.id_short,
    )

    shape_uri = compute_uri(
        template_id,
        path + "/shape",
    )

    range_class = ensure_aas_class(
        graph,
        "Range",
        "AAS Range",
    )

    graph.add(
        (
            property_uri,
            RDF.type,
            OWL.ObjectProperty,
        )
    )

    graph.add(
        (
            property_uri,
            RDFS.label,
            Literal(
                "has" + element.id_short
            ),
        )
    )

    graph.add(
        (
            shape_uri,
            RDF.type,
            semanticDict["SH"]["PropertyShape"],
        )
    )

    graph.add(
        (
            shape_uri,
            RDFS.label,
            Literal(
                make_shape_label(
                    element.id_short
                )
            ),
        )
    )

    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["path"],
            property_uri,
        )
    )

    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["class"],
            range_class,
        )
    )

    min_count, max_count = get_cardinality(
        element
    )

    add_cardinality_constraints(
        graph,
        shape_uri,
        min_count,
        max_count,
    )

    lift_semantic_id(
        graph,
        template_id,
        element,
        path,
    )

    graph.add(
        (
            parent_shape,
            semanticDict["SH"]["property"],
            shape_uri,
        )
    )

def lift_smc(
    graph: Graph,
    template_id: str,
    element,
    parent_path: str,
    parent_shape: URIRef,
    domain: str,
):
    path = build_path(
        parent_path,
        element.id_short,
    )

    property_uri = make_semantic_predicate(
        domain,
        element.id_short,
    )

    shape_uri = compute_uri(
        template_id,
        path + "/shape",
    )

    smc_class = ensure_aas_class(
        graph,
        "SMC",
        "Submodel Element Collection",
    )

    graph.add(
        (
            property_uri,
            RDF.type,
            OWL.ObjectProperty,
        )
    )

    graph.add(
        (
            property_uri,
            RDFS.label,
            Literal(
                "has" + element.id_short
            ),
        )
    )

    # PropertyShape for the SMC relationship
    graph.add(
        (
            shape_uri,
            RDF.type,
            semanticDict["SH"]["PropertyShape"],
        )
    )

    graph.add(
        (
            shape_uri,
            RDFS.label,
            Literal(
                make_shape_label(
                    element.id_short
                )
            ),
        )
    )

    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["path"],
            property_uri,
        )
    )

    # The value reached through this property must be an SMC
    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["class"],
            smc_class,
        )
    )

    min_count, max_count = get_cardinality(element)

    add_cardinality_constraints(
        graph,
        shape_uri,
        min_count,
        max_count,
    )

    graph.add(
        (
            parent_shape,
            semanticDict["SH"]["property"],
            shape_uri,
        )
    )

    # NodeShape for the contents of this SMC
    child_shape = compute_uri(
        template_id,
        path + "/nodeShape",
    )

    graph.add(
        (
            child_shape,
            RDF.type,
            semanticDict["SH"]["NodeShape"],
        )
    )

    graph.add(
        (
            child_shape,
            RDFS.label,
            Literal(
                make_node_shape_label(
                    element.id_short
                )
            ),
        )
    )

    # IMPORTANT:
    # Do NOT use sh:targetClass aas:SMC here.
    #
    # The child shape is applied through sh:node from
    # the parent PropertyShape.

    graph.add(
        (
            shape_uri,
            semanticDict["SH"]["node"],
            child_shape,
        )
    )

    lift_elements(
        graph=graph,
        template_id=template_id,
        elements=element.value,
        parent_path=path,
        parent_shape=child_shape,
        domain=domain,
    )

def resolve_model_reference_uri(
    reference,
    instance_id: str,
) -> URIRef:

    if reference is None:
        raise ValueError(
            "Relationship reference is None."
        )

    if not reference.keys:
        raise ValueError(
            "Relationship reference contains no keys."
        )

    submodel_id = None
    path_parts = []

    for key in reference.keys:

        key_value = str(
            key.value
        )

        if key.type == KeyTypes.SUBMODEL:

            submodel_id = key_value

        else:

            path_parts.append(
                key_value
            )

    if submodel_id is None:
        raise ValueError(
            "ModelReference does not contain "
            "a Submodel key."
        )

    if submodel_id == instance_id:

        path = ".".join(
            path_parts
        )

        return compute_uri(
            instance_id,
            path,
        )

    if path_parts:

        return URIRef(
            submodel_id
            + "#"
            + ".".join(path_parts)
        )

    return URIRef(
        submodel_id
    )

def lift_relationship(
    graph: Graph,
    instance_id: str,
    element,
    parent_path: str,
    parent_uri: URIRef,
    domain: str,
):
    path = build_path(
        parent_path,
        element.id_short,
    )

    element_uri = compute_uri(
        instance_id,
        path,
    )

    graph.add(
        (
            element_uri,
            RDF.type,
            semanticDict["AAS"]["RelationshipElement"],
        )
    )

    graph.add(
        (
            element_uri,
            RDFS.label,
            Literal(
                element.id_short
            ),
        )
    )

    predicate = make_semantic_predicate(
        domain,
        element.id_short,
    )

    graph.add(
        (
            parent_uri,
            predicate,
            element_uri,
        )
    )

    if element.first is not None:

        first_uri = resolve_model_reference_uri(
            element.first,
            instance_id,
        )

        graph.add(
            (
                element_uri,
                semanticDict["AAS"]["first"],
                first_uri,
            )
        )

    if element.second is not None:

        second_uri = resolve_model_reference_uri(
            element.second,
            instance_id,
        )

        graph.add(
            (
                element_uri,
                semanticDict["AAS"]["second"],
                second_uri,
            )
        )

    lift_semantic_id(
        graph,
        instance_id,
        element,
        path,
    )


def build_template_graph(
    submodel,
    domain: str,
) -> Graph:

    graph = Graph()

    bind_common_namespaces(
        graph,
        domain,
    )

    lift_template(
        submodel,
        graph,
        domain,
    )

    return graph


def main(domain,template_file):

    with open(
        template_file,
        "r",
        encoding="utf-8",
    ) as f:

        model = json.load(f)

    template = (
        aas_jsonization.submodel_from_jsonable(
            model
        )
    )

    print()
    print(
        "=========================================="
    )
    print(
        "AAS TEMPLATE LIFTING"
    )
    print(
        "=========================================="
    )

    print(
        f"Template ID: {template.id}"
    )

    print(
        f"Template idShort: {template.id_short}"
    )

    graph = build_template_graph(
        template,
        domain,
    )

    print()
    print(
        "=========================================="
    )
    print(
        "GENERATED TEMPLATE GRAPH"
    )
    print(
        "=========================================="
    )

    print(
        f"Total triples: {len(graph)}"
    )

    print()

    print(
        graph.serialize(
            format="turtle"
        )
    )

    template_graph_uri = compute_uri(
        template.id
    )

    push_graph_to_graphdb(
        graph,
        template_graph_uri,
    )

    print()
    print(
        "=========================================="
    )
    print(
        "TEMPLATE LIFTING COMPLETE"
    )
    print(
        "=========================================="
    )


if __name__ == "__main__":
    
    template_data = {"ecad":"ecad_template.json","dexpi":"dexpi_template.json"}
    
    for domain,template_file in template_data.items():
        main(domain,template_file)