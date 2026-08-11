'''
Created on Aug 10, 2026

@author: haris
AAS Template Lifting

Transforms an AAS Submodel Template into:
    - OWL classes/properties
    - SHACL NodeShapes
    - SHACL PropertyShapes
'''
from rdflib import (
    Graph,
    URIRef,
    Literal,
)

from rdflib.namespace import (
    RDF,
    RDFS,
    OWL,
)

import aas_core3_1.types as aas_types
import aas_core3_1.jsonization as aas_jsonization

from utils import (
    semanticDict,
    compute_uri,
    map_xsd_datatype,
    get_cardinality,
    create_graph,
    load_submodel,
    push_to_graphdb,
    lift_semantic_id,
)


# =============================================================================
# SHACL LABELS
# =============================================================================

def label_node_shape(
    graph: Graph,
    shape_node: URIRef,
    name: str,
    path: str,
):
    """
    Properly label a SHACL NodeShape.
    """

    graph.add(
        (
            shape_node,
            semanticDict["SH"].name,
            Literal(name),
        )
    )

    graph.add(
        (
            shape_node,
            RDFS.label,
            Literal(
                f"SHACL Node Shape: {name}"
            ),
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].description,
            Literal(
                f"Node shape for AAS path '{path}'"
            ),
        )
    )


def label_property_shape(
    graph: Graph,
    shape_node: URIRef,
    name: str,
    path: str,
):
    """
    Properly label a SHACL PropertyShape.
    """

    graph.add(
        (
            shape_node,
            semanticDict["SH"].name,
            Literal(name),
        )
    )

    graph.add(
        (
            shape_node,
            RDFS.label,
            Literal(
                f"SHACL Property Shape: {name}"
            ),
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].description,
            Literal(
                f"Property shape for AAS path '{path}'"
            ),
        )
    )


# =============================================================================
# CARDINALITY
# =============================================================================

def apply_cardinality(
    graph: Graph,
    shape_node: URIRef,
    element,
):
    """
    Apply the AAS Cardinality qualifier to a SHACL shape.
    """

    min_count, max_count = get_cardinality(
        element
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].minCount,
            Literal(min_count),
        )
    )

    if max_count is not None:

        graph.add(
            (
                shape_node,
                semanticDict["SH"].maxCount,
                Literal(max_count),
            )
        )


# =============================================================================
# PROPERTY
# =============================================================================

def lift_property(
    graph: Graph,
    submodel_id: str,
    element: aas_types.Property,
    parent_path: str,
    parent_shape: URIRef,
):
    """
    Lift template Property.
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + element.id_short
        )

    else:

        path = element.id_short

    # -------------------------------------------------------------------------
    # Stable TEMPLATE property URI
    # -------------------------------------------------------------------------

    property_uri = compute_uri(
        submodel_id,
        path,
    )

    # -------------------------------------------------------------------------
    # SHACL PropertyShape
    # -------------------------------------------------------------------------

    shape_node = compute_uri(
        submodel_id,
        path + "/shape",
    )

    # -------------------------------------------------------------------------
    # OWL DatatypeProperty
    # -------------------------------------------------------------------------

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
                element.id_short
            ),
        )
    )

    # -------------------------------------------------------------------------
    # PropertyShape
    # -------------------------------------------------------------------------

    graph.add(
        (
            shape_node,
            RDF.type,
            semanticDict["SH"].PropertyShape,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].path,
            property_uri,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].datatype,
            map_xsd_datatype(
                element.value_type
            ),
        )
    )

    # -------------------------------------------------------------------------
    # Cardinality from qualifier
    # -------------------------------------------------------------------------

    apply_cardinality(
        graph,
        shape_node,
        element,
    )

    # -------------------------------------------------------------------------
    # Labels
    # -------------------------------------------------------------------------

    label_property_shape(
        graph,
        shape_node,
        element.id_short,
        path,
    )

    # -------------------------------------------------------------------------
    # Attach to parent NodeShape
    # -------------------------------------------------------------------------

    graph.add(
        (
            parent_shape,
            semanticDict["SH"].property,
            shape_node,
        )
    )

    # -------------------------------------------------------------------------
    # Semantic ID
    # -------------------------------------------------------------------------

    lift_semantic_id(
        graph,
        submodel_id,
        element,
        path,
    )


# =============================================================================
# RANGE
# =============================================================================

def lift_range(
    graph: Graph,
    submodel_id: str,
    element: aas_types.Range,
    parent_path: str,
    parent_shape: URIRef,
):
    """
    Lift template Range.
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + element.id_short
        )

    else:

        path = element.id_short

    property_uri = compute_uri(
        submodel_id,
        path,
    )

    shape_node = compute_uri(
        submodel_id,
        path + "/shape",
    )

    # -------------------------------------------------------------------------
    # Interval
    # -------------------------------------------------------------------------

    graph.add(
        (
            semanticDict["AAS"].Interval,
            RDF.type,
            OWL.Class,
        )
    )

    graph.add(
        (
            semanticDict["AAS"].Interval,
            RDFS.label,
            Literal(
                "AAS Range Interval"
            ),
        )
    )

    # -------------------------------------------------------------------------
    # OWL property
    # -------------------------------------------------------------------------

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
                element.id_short
            ),
        )
    )

    # -------------------------------------------------------------------------
    # SHACL PropertyShape
    # -------------------------------------------------------------------------

    graph.add(
        (
            shape_node,
            RDF.type,
            semanticDict["SH"].PropertyShape,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].path,
            property_uri,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].class_,
            semanticDict["AAS"].Interval,
        )
    )

    apply_cardinality(
        graph,
        shape_node,
        element,
    )

    label_property_shape(
        graph,
        shape_node,
        element.id_short,
        path,
    )

    graph.add(
        (
            parent_shape,
            semanticDict["SH"].property,
            shape_node,
        )
    )

    lift_semantic_id(
        graph,
        submodel_id,
        element,
        path,
    )


# =============================================================================
# SUBMODEL ELEMENT COLLECTION
# =============================================================================

def lift_smc(
    graph: Graph,
    submodel_id: str,
    element: aas_types.SubmodelElementCollection,
    parent_path: str,
    domain: str,
    parent_shape: URIRef,
):
    """
    Lift a template SubmodelElementCollection.

    A collection creates TWO SHACL resources:

        PropertyShape
            |
            +-- sh:path
            +-- sh:minCount
            +-- sh:maxCount
            +-- sh:node
                     |
                     v
                 NodeShape
                     |
                     +-- child PropertyShapes
    """

    # -------------------------------------------------------------------------
    # Path
    # -------------------------------------------------------------------------

    if parent_path:

        path = (
            parent_path
            + "."
            + element.id_short
        )

    else:

        path = element.id_short

    # -------------------------------------------------------------------------
    # Property URI
    # -------------------------------------------------------------------------

    property_uri = compute_uri(
        submodel_id,
        path,
    )

    # -------------------------------------------------------------------------
    # PropertyShape
    # -------------------------------------------------------------------------

    property_shape = compute_uri(
        submodel_id,
        path + "/shape",
    )

    # -------------------------------------------------------------------------
    # NodeShape for collection contents
    # -------------------------------------------------------------------------

    node_shape = compute_uri(
        submodel_id,
        path + "/node-shape",
    )

    # -------------------------------------------------------------------------
    # OWL ObjectProperty
    # -------------------------------------------------------------------------

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
                element.id_short
            ),
        )
    )

    # -------------------------------------------------------------------------
    # PropertyShape
    # -------------------------------------------------------------------------

    graph.add(
        (
            property_shape,
            RDF.type,
            semanticDict["SH"].PropertyShape,
        )
    )

    graph.add(
        (
            property_shape,
            semanticDict["SH"].path,
            property_uri,
        )
    )

    graph.add(
        (
            property_shape,
            semanticDict["SH"].class_,
            semanticDict["AAS"].SMC,
        )
    )

    # Cardinality
    apply_cardinality(
        graph,
        property_shape,
        element,
    )

    # PropertyShape -> NodeShape
    graph.add(
        (
            property_shape,
            semanticDict["SH"].node,
            node_shape,
        )
    )

    # Labels
    label_property_shape(
        graph,
        property_shape,
        element.id_short,
        path,
    )

    # Attach property to parent
    graph.add(
        (
            parent_shape,
            semanticDict["SH"].property,
            property_shape,
        )
    )

    # -------------------------------------------------------------------------
    # NodeShape
    # -------------------------------------------------------------------------

    graph.add(
        (
            node_shape,
            RDF.type,
            semanticDict["SH"].NodeShape,
        )
    )

    label_node_shape(
        graph,
        node_shape,
        element.id_short,
        path,
    )

    # -------------------------------------------------------------------------
    # Recurse into collection
    # -------------------------------------------------------------------------

    lift_elements(
        graph,
        submodel_id,
        element.value,
        path,
        domain,
        node_shape,
    )

    # Semantic ID
    lift_semantic_id(
        graph,
        submodel_id,
        element,
        path,
    )


# =============================================================================
# RELATIONSHIP
# =============================================================================

def lift_relationship(
    graph: Graph,
    submodel_id: str,
    element: aas_types.RelationshipElement,
    parent_path: str,
    parent_shape: URIRef,
):
    """
    Lift RelationshipElement template.
    """

    if parent_path:

        path = (
            parent_path
            + "."
            + element.id_short
        )

    else:

        path = element.id_short

    relation_uri = URIRef(
        f"{submodel_id}#{element.id_short}"
    )

    shape_node = compute_uri(
        submodel_id,
        path + "/shape",
    )

    # OWL property
    graph.add(
        (
            relation_uri,
            RDF.type,
            OWL.ObjectProperty,
        )
    )

    graph.add(
        (
            relation_uri,
            RDFS.label,
            Literal(
                element.id_short
            ),
        )
    )

    # SHACL PropertyShape
    graph.add(
        (
            shape_node,
            RDF.type,
            semanticDict["SH"].PropertyShape,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].path,
            relation_uri,
        )
    )

    graph.add(
        (
            shape_node,
            semanticDict["SH"].class_,
            semanticDict["AAS"].SubmodelElement,
        )
    )

    apply_cardinality(
        graph,
        shape_node,
        element,
    )

    label_property_shape(
        graph,
        shape_node,
        element.id_short,
        path,
    )

    graph.add(
        (
            parent_shape,
            semanticDict["SH"].property,
            shape_node,
        )
    )

    lift_semantic_id(
        graph,
        submodel_id,
        element,
        path,
    )


# =============================================================================
# DISPATCHER
# =============================================================================

def lift_elements(
    graph: Graph,
    submodel_id: str,
    elements,
    parent_path: str,
    domain: str,
    parent_shape: URIRef,
):
    """
    Recursively lift template elements.
    """

    for element in elements:

        if isinstance(
            element,
            aas_types.Property,
        ):

            lift_property(
                graph,
                submodel_id,
                element,
                parent_path,
                parent_shape,
            )

        elif isinstance(
            element,
            aas_types.Range,
        ):

            lift_range(
                graph,
                submodel_id,
                element,
                parent_path,
                parent_shape,
            )

        elif isinstance(
            element,
            aas_types.SubmodelElementCollection,
        ):

            lift_smc(
                graph,
                submodel_id,
                element,
                parent_path,
                domain,
                parent_shape,
            )

        elif isinstance(
            element,
            aas_types.RelationshipElement,
        ):

            lift_relationship(
                graph,
                submodel_id,
                element,
                parent_path,
                parent_shape,
            )

        else:

            print(
                "Warning: unsupported template "
                f"element: {type(element).__name__}"
            )


# =============================================================================
# ROOT TEMPLATE
# =============================================================================

def template_lifting(
    submodel,
    domain: str,
):
    """
    Lift the complete AAS template.
    """

    graph = create_graph(
        submodel.id,
        domain,
    )

    # -------------------------------------------------------------------------
    # Root class
    # -------------------------------------------------------------------------

    template_class = compute_uri(
        submodel.id,
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
            Literal(
                submodel.id_short
            ),
        )
    )

    # -------------------------------------------------------------------------
    # Root NodeShape
    # -------------------------------------------------------------------------

    root_shape = compute_uri(
        submodel.id,
        "shape",
    )

    graph.add(
        (
            root_shape,
            RDF.type,
            semanticDict["SH"].NodeShape,
        )
    )

    graph.add(
        (
            root_shape,
            semanticDict["SH"].targetClass,
            template_class,
        )
    )

    label_node_shape(
        graph,
        root_shape,
        submodel.id_short,
        submodel.id_short,
    )

    # -------------------------------------------------------------------------
    # Common AAS classes
    # -------------------------------------------------------------------------

    graph.add(
        (
            semanticDict["AAS"].SMC,
            RDF.type,
            OWL.Class,
        )
    )

    graph.add(
        (
            semanticDict["AAS"].SMC,
            RDFS.label,
            Literal(
                "AAS Submodel Element Collection"
            ),
        )
    )

    graph.add(
        (
            semanticDict["AAS"].SubmodelElement,
            RDF.type,
            OWL.Class,
        )
    )

    graph.add(
        (
            semanticDict["AAS"].SubmodelElement,
            RDFS.label,
            Literal(
                "AAS Submodel Element"
            ),
        )
    )

    # -------------------------------------------------------------------------
    # Elements
    # -------------------------------------------------------------------------

    lift_elements(
        graph,
        submodel.id,
        submodel.submodel_elements,
        "",
        domain,
        root_shape,
    )

    return graph

def main(filename,domain):


    submodel = load_submodel(
        filename    )

    graph = template_lifting(
        submodel,
        domain,
    )

    print(f"Template graph contains {len(graph)} triples.")

    push_to_graphdb(
            graph,
            submodel.id,
        )

if __name__ == "__main__":
    
    file_dict = {"dexpi":"dexpi_template.json"} # "ecad":"sample_ecad.json",
    
    for domain,filename in file_dict.items():
        main(filename,domain)