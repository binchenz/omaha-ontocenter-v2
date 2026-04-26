from app.services.omaha import OmahaService

GENERAL_CONFIG = """
datasources:
  - id: mysql_erp
    name: ERP Database
    type: sql
    connection:
      url: "sqlite:///:memory:"
ontology:
  objects:
    - name: Order
      datasource: mysql_erp
      source_entity: t_order
      description: Customer purchase order
      properties:
        - name: id
          type: integer
        - name: total_amount
          type: float
          semantic_type: currency_cny
        - name: status
          type: string
          semantic_type: order_status
      default_filters:
        - field: status
          operator: "!="
          value: "deleted"
  relationships: []
"""

service = OmahaService(GENERAL_CONFIG)
print('parse_config:', service.parse_config())
print('build_ontology:', service.build_ontology())
print('get_object_schema:', service.get_object_schema('Order'))
