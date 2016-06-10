def create_organizations():
    "caseA"
    "caseB"
    "caseC"
    "caseD"
    "caseALL"
    return


def create_cycle(org):
    Cycle.objects.create(name="2015 Annual",
                         organization = org,
                         start=datetime.datetime(2015,1,1),
                         end=datetime.datetime(2016,1,1)-datetime.timedelta(seconds=1))
    return


def createCases(org, tax_lots, properties):
    cycle = Cycle.objects.filter(organization=org).first()

    for (tl_def, prop_def) in itertools.product(tax_lots, properties):
        property = Property.objects.create()
        tax_lot = TaxLot.objects.create()

        prop_state = PropertyState.objects.get_or_create(**prop_def)
        taxlot_state = TaxLotState.objects.get_or_create(**tl_def)

        taxlot_view = TaxLotView.objects.get_or_create(taxlot = taxlot_state, cycle=cycle, state = taxlot_state)
        prop_view = PropertyView.objects.get_or_create(property=prop_state, cycle=cycle, state = prop_state)

        TaxLotProperty.objects.create(property_view = prop_view, taxlot_view = taxlot_view, cycle = cycle)

    return


def create_case_A_objects(org):
    tax_lots = [ {jurisdiction_taxlot_identifier:"1552813",
                  address: "050 Willow Ave SE",
                  city: "Rust",
                  number_buildings: 1}]

    properties = [{ building_portfolio_manager_identifier: 2264,
                    property_name: "University Inn",
                    address_line_1: "50 Willow Ave SE",
                    city: "Rust",
                    use_description: "Hotel",
                    site_eui: 125,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:12555,
                    owner: "ULLC",
                    owner_email: "ULLC@gmail.com",
                    owner_telephone: "213-852-1238",
                    property_notes: "Case A-1: 1 Property, 1 Tax Lot"}]

    create_cases(org, tax_lots, properties)
    return



def create_case_B_objects(org):
    tax_lots = [ {jurisdiction_taxlot_identifier:"",
                  address: "",
                  city: "",
                  number_buildings: 0}]

    properties = [{ building_portfolio_manager_identifier: 3020139,
                    property_name: ""Hilltop Condos,
                    address_line_1: "2655 Welstone Ave NE",
                    city: "Rust",
                    use_description: "Multi-family housing",
                    site_eui: 0,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:0,
                    owner: "",
                    owner_email: "",
                    owner_telephone: "",
                    property_notes: ""},
                  { building_portfolio_manager_identifier: 0,
                    property_name: "",
                    address_line_1: "",
                    city: "",
                    use_description: "",
                    site_eui: 0,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:0,
                    owner: "",
                    owner_email: "",
                    owner_telephone: "",
                    property_notes: ""},
                  { building_portfolio_manager_identifier: 0,
                    property_name: "",
                    address_line_1: "",
                    city: "",
                    use_description: "",
                    site_eui: 0,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:0,
                    owner: "",
                    owner_email: "",
                    owner_telephone: "",
                    property_notes: ""}]

    create_cases(org, tax_lots, properties)
    return



def create_case_C_objects(org):
    tax_lots = [ {jurisdiction_taxlot_identifier:"",
                  address: "",
                  city: "",
                  number_buildings: 0}]

    properties = [{ building_portfolio_manager_identifier: 0,
                    property_name: "",
                    address_line_1: "",
                    city: "",
                    use_description: "",
                    site_eui: 0,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:0,
                    owner: "",
                    owner_email: "",
                    owner_telephone: "",
                    property_notes: ""}]

    create_cases(org, tax_lots, properties)
    return


def create_case_D_objects(org):
    tax_lots = [ {jurisdiction_taxlot_identifier:"",
                  address: "",
                  city: "",
                  number_buildings: 0}]

    properties = [{ building_portfolio_manager_identifier: 0,
                    property_name: "",
                    address_line_1: "",
                    city: "",
                    use_description: "",
                    site_eui: 0,
                    year_ending: datetime.datetime(2015,12,31),
                    gross_floor_are:0,
                    owner: "",
                    owner_email: "",
                    owner_telephone: "",
                    property_notes: ""}]

    create_cases(org, tax_lots, properties)
    return
