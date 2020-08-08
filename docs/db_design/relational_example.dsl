// Can be view: https://dbdiagram.io/d/5f2d684908c7880b65c57a68

Table Tags as T {
  id int [pk, increment]
  name varchar
}

Table TagImplication as TI {
  tag_id int [ref: > T.id]
  implies_id int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data
}

Table TagParamDataInstance as TPDI {
  id int [pk, increment]
}

enum TagParamType {
  NumericIntRange
  NumericIntLower
  NumericIntUpper
  NumericRealRange
  NumericRealLower
  NumericRealUpper
  StringSet
}

Table TagParams as TP {
  tag_id int [ref: > T.id]
  index int 
  param_type TagParamType
}

Table TagParamData_NIR as RPD_NIR {
  data_instance int [ref: - TPDI.id]
  tag_id int [ref: > T.id]
  param_index int [ref: > TP.index]
  lower int
  upper int
}

Table TagParamData_NILU as RPD_NILU {
  data_instance int [ref: - TPDI.id]
  tag_id int [ref: > T.id]
  param_index int [ref: > TP.index]
  lower_upper int
}

Table TagParamData_NRR as RPD_NRR {
  data_instance int [ref: - TPDI.id]
  tag_id int [ref: > T.id]
  param_index int [ref: > TP.index]
  lower decimal
  upper decimal
}

Table TagParamData_NRLU as RPD_NRLU {
  data_instance int [ref: - TPDI.id]
  tag_id int [ref: > T.id]
  param_index int [ref: > TP.index]
  lower_upper decimal
}

Table Item as I {
  id int [pk, increment]
}

Table ItemTags as IT {
  item_id int [ref: > I.id] 
  tag_id int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data
}

Table ItemParams as IP {
  id int [pk, increment]
  item_id int [ref: > I.id]
  option_id int [ref: > IPO.id]
}

enum ParamType {
  Picture
  ShortTitle
  SubTitle
  ShortText
  BiggerText
}

Table ItemParamOptions as IPO {
  id int [pk, increment]
  name varchar
  type ParamType
}

Table ParamImageData as IPID {
  param_id int [ref: - IP.id]
  path text
}

Table ParamTitleText as IPTT {
  param_id int [ref: - IP.id]
  the_text tinytext
}

Table ParamShortText as IPST {
  param_id int [ref: - IP.id]
  the_text text
}

Table ParamBiggerText as IPBT {
  param_id int [ref: - IP.id]
  the_text mediumtext
}

Table ItemInstance as II {
  id int [pk, increment]
  item_id int [ref: > I.id]
}

Table ItemInstanceTags as IIT {
  item_instance_id int [ref: > II.id] 
  tag_id int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data
}

Table ItemInstanceParams as IIP {
  id int [pk, increment]
  item_instance_id int [ref: > II.id]
  option_id int [ref: > IIPO.id]
}

Table ItemInstanceParamOptions as IIPO {
  id int [pk, increment]
  name varchar
  type ParamType
}

Table User as U {
  id int [pk, increment]
  name text(1000)
}

Table UserRoals as UR {
  user_id int [ref: > U.id]
  role_id int [ref: > R.id]
}

Table Role as R {
  id int [pk, increment]
  name text(1000)
  priority int // 0 highest
}

enum RolePermission {
  AddItem
  AddInstance
  CreateTag
  AssignTag
  // ect...
}

Table AssignedPermissions as AP {
  role_id int [ref: > R.id]
  permission RolePermission
  granted boolean
}

Table ItemRelations as IR {
  id int [pk, increment]
  name text(1000)
}

Table ItemRelationImplies as IRI {
  relation_id int [ref: > IR.id]
  implied_tag int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data, and that data is the same every application
}

Table ItemRelationImplicationApplication as IRIA {
  item_reation_application_id int [ref: > IRA.id]
  implied_tag int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data, and that data might be different every application
}

Table ItemRelationApplication as IRA {
  id int [pk, increment]
  item_istance_id int [ref: > II.id]
  relation_id int [ref: > IIR.id]
  user_id int [ref: > U.id]
}

Table ItemInstanceRelations as IIR {
  id int [pk, increment]
  name text(1000)
}

Table ItemIstanceRelationImplies as IIRI {
  relation_id int [ref: > IIR.id]
  implied_tag int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data, and that data is the same every application
}

Table ItemInstanceRelationImplicationApplication as IIRIA {
  item_reation_application_id int [ref: > IIRA.id]
  implied_tag int [ref: > T.id]
  data_instance int [ref: - TPDI.id] // Only used if the implied tag need data, and that data might be different every application
}

Table ItemInstanceRelationApplication as IIRA {
  id int [pk, increment]
  item_instance_id int [ref: > II.id]
  relation_id int [ref: > IIR.id]
  user_id int [ref: > U.id]
}









