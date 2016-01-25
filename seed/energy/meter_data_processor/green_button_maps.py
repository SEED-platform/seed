global usage_kind_map
global reading_kind_map
global uom_map

usage_kind_map = {'0':'electricity',
                  '1':'gas',
                  '2':'water',
                  '3':'time',
                  '4':'heat',
                  '5':'refuse',      # refuse water service
                  '6':'sewerage',
                  '7':'rates',       # Rates (e.g. tax, charge, toll, duty, tariff, etc.) service.
                  '8':'tvLicence',
                  '9':'internet'};

reading_kind_map = {'0':'none',                   # Not Applicable
                    '2':'apparentPowerFactor',
                    '3':'currency',                # funds
                    '4':'current',
                    '5':'currentAngle',
                    '6':'currentImbalance',
                    '7':'date',
                    '8':'demand',
                    '9':'distance',
                    '10':'distortionVoltAmperes',
                    '11':'energization',
                    '12':'energy',
                    '13':'energizationLoadSide',
                    '14':'fan',
                    '15':'frequency',
                    '16':'Funds',                  # Dup with currency
                    '17':'ieee1366ASAI',
                    '18':'ieee1366ASIDI',
                    '19':'ieee1366ASIFI',
                    '20':'ieee1366CAIDI',
                    '21':'ieee1366CAIFI',
                    '22':'ieee1366CEMIn',
                    '23':'ieee1366CEMSMIn',
                    '24':'ieee1366CTAIDI',
                    '25':'ieee1366MAIFI',
                    '26':'ieee1366MAIFIe',
                    '27':'ieee1366SAIDI',
                    '28':'ieee1366SAIFI',
                    '31':'lineLosses',
                    '32':'losses',
                    '33':'negativeSequence',
                    '34':'phasorPowerFactor',
                    '35':'phasorReactivePower',
                    '36':'positiveSequence',
                    '37':'power',
                    '38':'powerFactor',
                    '40':'quantityPower',
                    '41':'sag',                     # or Voltage Dip
                    '42':'swell',
                    '43':'switchPosition',
                    '44':'tapPosition',
                    '45':'tariffRate',
                    '46':'temperature',
                    '47':'totalHarmonicDistortion',
                    '48':'transformerLosses',
                    '49':'unipedeVoltageDip10to15',
                    '50':'unipedeVoltageDip15to30',
                    '51':'unipedeVoltageDip30to60',
                    '52':'unipedeVoltageDip60to90',
                    '53':'unipedeVoltageDip90to100',
                    '54':'voltage',
                    '55':'voltageAngle',
                    '56':'voltageExcursion',
                    '57':'voltageImbalance',
                    '58':'volume',                      # Clarified from Ed. 1. to indicate fluid volume
                    '59':'zeroFlowDuration',
                    '60':'zeroSequence',
                    '64':'distortionPowerFactor',
                    '81':'frequencyExcursion',          # Usually expressed as a count
                    '90':'applicationContext',
                    '91':'apTitle',
                    '92':'assetNumber',
                    '93':'bandwidth',
                    '94':'batteryVoltage',
                    '95':'broadcastAddress',
                    '96':'deviceAddressType1',
                    '97':'deviceAddressType2',
                    '98':'deviceAddressType3',
                    '99':'deviceAddressType4',
                    '100':'deviceClass',
                    '101':'electronicSerialNumber',
                    '102':'endDeviceID',
                    '103':'groupAddressType1',
                    '104':'groupAddressType2',
                    '105':'groupAddressType3',
                    '106':'groupAddressType4',
                    '107':'ipAddress',
                    '108':'macAddress',
                    '109':'mfgAssignedConfigurationID',
                    '110':'mfgAssignedPhysicalSerialNumber',
                    '111':'mfgAssignedProductNumber',
                    '112':'mfgAssignedUniqueCommunicationAddress',
                    '113':'multiCastAddress',
                    '114':'oneWayAddress',
                    '115':'signalStrength',
                    '116':'twoWayAddress',
                    '117':'signaltoNoiseRatio',                 #  Moved here from Attribute #9 UOM
                    '118':'alarm',
                    '119':'batteryCarryover',
                    '120':'dataOverflowAlarm',
                    '121':'demandLimit',
                    '122':'demandReset',                        # Usually expressed as a count as part of a billing cycle
                    '123':'diagnostic',
                    '124':'emergencyLimit',
                    '125':'encoderTamper',
                    '126':'ieee1366MomentaryInterruption',
                    '127':'ieee1366MomentaryInterruptionEvent',
                    '128':'ieee1366SustainedInterruption',
                    '129':'interruptionBehaviour',
                    '130':'inversionTamper',
                    '131':'loadInterrupt',
                    '132':'loadShed',
                    '133':'maintenance',
                    '134':'physicalTamper',
                    '135':'powerLossTamper',
                    '136':'powerOutage',
                    '137':'powerQuality',
                    '138':'powerRestoration',
                    '139':'programmed',
                    '140':'pushbutton',
                    '141':'relayActivation',
                    '142':'relayCycle',                    # Usually expressed as a count
                    '143':'removalTamper',
                    '144':'reprogrammingTamper',
                    '145':'reverseRotationTamper',
                    '146':'switchArmed',
                    '147':'switchDisabled',
                    '148':'tamper',
                    '149':'watchdogTimeout',
                    '150':'billLastPeriod',                    # Customer's bill for the previous billing period (Currency)
                    '151':'billToDate',                        # Customer's bill, as known thus far within the present billing period (Currency)
                    '152':'billCarryover',                     # Customer's bill for the (Currency)
                    '153':'connectionFee',                     # Monthly fee for connection to commodity.
                    '154':'audibleVolume',                     # Sound
                    '155':'volumetricFlow'
    };
    
uom_map = { '61':'VA',         # Apparent power, Volt Ampere (See also real power and reactive power.), VA
            '38':'W',         # Real power, Watt. By definition, one Watt equals one Joule per second. Electrical power may have real and reactive components. The real portion of electrical power (I2R) or VIcos, is expressed in Watts. (See also apparent power and reactive power.), W
            '63':'VAr',         # Reactive power, Volt Ampere reactive. The "reactive" or "imaginary" component of electrical power (VISin). (See also real power and apparent power)., VAr
            '71':'VAh',         # Apparent energy, Volt Ampere hours, VAh
            '72':'Wh',         # Real energy, Watt hours, Wh
            '73':'VArh',         # Reactive energy, Volt Ampere reactive hours, VArh
            '29':'V',         # Electric potential, Volt (W/A), V
            '30':'ohm',         # Electric resistance, Ohm (V/A), O
            '5':'A',         # Current, ampere, A
            '25':'F',         # Electric capacitance, Farad (C/V), C
            '28':'H',         # Electric inductance, Henry (Wb/A), H
            '23':'degC',         # Relative temperature in degrees Celsius. In the SI unit system the symbol is oC. Electric charge is measured in coulomb that has the unit symbol C. To distinguish degree Celsius from coulomb the symbol used in the UML is degC. Reason for not using oC is the special character o is difficult to manage in software.
            '27':'sec',         # Time, seconds, s
            '159':'min',         # Time, minute = s * 60, min
            '160':'h',         # Time, hour = minute * 60, h
            '9':'deg',         # Plane angle, degrees, deg
            '10':'rad',         # Plane angle, Radian (m/m), rad
            '31':'J',         # Energy joule, (N*m = C*V = W*s), J
            '32':'n',         # Force newton, (kg m/s2), N
            '53':'siemens',         # Electric conductance, Siemens (A / V = 1 / O), S
            '0':'none',         # N/A, None
            '33':'Hz',         # Frequency hertz, (1/s), Hz
            '3':'g',         # Mass in gram, g
            '39':'pa',         # Pressure, Pascal (N/m2)(Note: the absolute or relative measurement of pressure is implied with this entry. See below for more explicit forms.), Pa
            '2':'m',         # Length, meter, m
            '41':'m2',         # Area, square meter, m2
            '42':'m3',         # Volume, cubic meter, m3
            '69':'A2',         # Amps squared, amp squared, A2
            '105':'A2h',         # ampere-squared, Ampere-squared hour, A2h
            '70':'A2s',         # Amps squared time, square amp second, A2s
            '106':'Ah',         # Ampere-hours, Ampere-hours, Ah
            '152':'APerA',         # Current, Ratio of Amperages, A/A
            '103':'APerM',         # A/m, magnetic field strength, Ampere per metre, A/m
            '68':'As',         # Amp seconds, amp seconds, As
            '79':'b',         # Sound pressure level, Bel, acoustic, Combine with multiplier prefix "d" to form decibels of Sound Pressure Level"dB (SPL).", B (SPL)
            '113':'bm',         # Signal Strength, Bel-mW, normalized to 1mW. Note: to form "dBm" combine "Bm" with multiplier "d". Bm
            '22':'bq',         # Radioactivity, Becquerel (1/s), Bq
            '132':'btu',         # Energy, British Thermal Units, BTU
            '133':'btuPerH',         # Power, BTU per hour, BTU/h
            '8':'cd',         # Luminous intensity, candela, cd
            '76':'char',         # Number of characters, characters, char
            '75':'HzPerSec',         # Rate of change of frequency, hertz per second, Hz/s
            '114':'code',         # Application Value, encoded value, code
            '65':'cosTheta',         # Power factor, Dimensionless, cos
            '111':'count',         # Amount of substance, counter value, count
            '119':'ft3',         # Volume, cubic feet, ft3
            '120':'ft3compensated',         # Volume, cubic feet, ft3(compensated)
            '123':'ft3compensatedPerH',         # Volumetric flow rate, compensated cubic feet per hour, ft3(compensated)/h
            '78':'gM2',         # Turbine inertia, gram*meter2 (Combine with multiplier prefix "k" to form kg*m2.), gm2
            '144':'gPerG',         # Concentration, The ratio of the mass of a solute divided by the mass of the solution., g/g
            '21':'gy',         # Absorbed dose, Gray (J/kg), GY
            '150':'HzPerHz',         # Frequency, Rate of frequency change, Hz/Hz
            '77':'charPerSec',         # Data rate, characters per second, char/s
            '130':'imperialGal',         # Volume, imperial gallons, ImperialGal
            '131':'imperialGalPerH',         # Volumetric flow rate, Imperial gallons per hour, ImperialGal/h
            '51':'jPerK',         # Heat capacity, Joule/Kelvin, J/K
            '165':'jPerKg',         # Specific energy, Joules / kg, J/kg
            '6':'K',         # Temperature, Kelvin, K
            '158':'kat',         # Catalytic activity, katal = mol / s, kat
            '47':'kgM',         # Moment of mass ,kilogram meter (kg*m), M
            '48':'kgPerM3',         # Density, gram/cubic meter (combine with prefix multiplier "k" to form kg/ m3), g/m3
            '134':'litre',         # Volume, litre = dm3 = m3/1000., L
            '157':'litreCompensated',         # Volume, litre, with the value compensated for weather effects, L(compensated)
            '138':'litreCompensatedPerH',         # Volumetric flow rate, litres (compensated) per hour, L(compensated)/h
            '137':'litrePerH',         # Volumetric flow rate, litres per hour, L/h
            '143':'litrePerLitre',         # Concentration, The ratio of the volume of a solute divided by the volume of the solution., L/L
            '82':'litrePerSec',         # Volumetric flow rate, Volumetric flow rate, L/s
            '156':'litreUncompensated',         # Volume, litre, with the value uncompensated for weather effects., L(uncompensated)
            '139':'litreUncompensatedPerH',         # Volumetric flow rate, litres (uncompensated) per hour, L(uncompensated)/h
            '35':'lm',         # Luminous flux, lumen (cd sr), Lm
            '34':'lx',         # Illuminance lux, (lm/m2), L(uncompensated)/h
            '49':'m2PerSec',         # Viscosity, meter squared / second, m2/s
            '167':'m3compensated',         # Volume, cubic meter, with the value compensated for weather effects., m3(compensated)
            '126':'m3compensatedPerH',         # Volumetric flow rate, compensated cubic meters per hour, 3(compensated)/h
            '125':'m3PerH',         # Volumetric flow rate, cubic meters per hour, m3/h
            '45':'m3PerSec',         # m3PerSec, cubic meters per second, m3/s
            '166':'m3uncompensated',         # m3uncompensated, cubic meter, with the value uncompensated for weather effects., m3(uncompensated)
            '127':'m3uncompensatedPerH',         # Volumetric flow rate, uncompensated cubic meters per hour, m3(uncompensated)/h
            '118':'meCode',         # EndDeviceEvent, value to be interpreted as a EndDeviceEventCode, meCode
            '7':'mol',         # Amount of substance, mole, mol
            '147':'molPerKg',         # Concentration, Molality, the amount of solute in moles and the amount of solvent in kilograms., mol/kg
            '145':'molPerM3',         # Concentration, The amount of substance concentration, (c), the amount of solvent in moles divided by the volume of solution in m3., mol/ m3
            '146':'molPerMol',         # Concentration, Molar fraction (), the ratio of the molar amount of a solute divided by the molar amount of the solution.,mol/mol
            '80':'money',         # Monetary unit, Generic money (Note: Specific monetary units are identified the currency class).
            '148':'mPerM',         # Length, Ratio of length, m/m
            '46':'mPerM3',         # Fuel efficiency, meters / cubic meter, m/m3
            '43':'mPerSec',         # Velocity, meters per second (m/s), m/s
            '44':'mPerSec2',         # Acceleration, meters per second squared, m/s2
            '102':'ohmM',         # resistivity,  (rho), m
            '155':'paA',         # Pressure, Pascal, absolute pressure, PaA
            '140':'paG',         # Pressure, Pascal, gauge pressure, PaG
            '141':'psiA',         # Pressure, Pounds per square inch, absolute, psiA
            '142':'psiG',         # Pressure, Pounds per square inch, gauge, psiG
            '100':'q',         # Quantity power, Q, Q
            '161':'q45',         # Quantity power, Q measured at 45o, Q45
            '163':'q45h',         # Quantity energy, Q measured at 45o, Q45h
            '162':'q60',         # Quantity power, Q measured at 60o, Q60
            '164':'q60h',         # Quantity energy, Qh measured at 60o, Q60h
            '101':'qh',         # Quantity energy, Qh, Qh
            '54':'radPerSec',         # Angular velocity, radians per second, rad/s
            '154':'rev',         # Amount of rotation, Revolutions, rev
            '4':'revPerSec',         # Rotational speed, Rotations per second, rev/s
            '149':'secPerSec',       # Time, Ratio of time (can be combined with an multiplier prefix to show rates such as a clock drift rate, e.g. "us/s"), s/s
            '11':'sr',         # Solid angle, Steradian (m2/m2), sr
            '109':'status',         # State, "1" = "true", "live", "on", "high", "set"; "0" = "false", "dead", "off", "low", "cleared". Note: A Boolean value is preferred but other values may be supported, status
            '24':'sv',         # Doe equivalent, Sievert (J/kg), Sv
            '37':'t',         # Magnetic flux density, Tesla (Wb/m2), T
            '169':'therm',         # Energy, Therm, therm
            '108':'timeStamp',         # Timestamp, time and date per ISO 8601 format, timeStamp
            '128':'usGal',         # Volume, US gallons, Gal
            '129':'usGalPerH',         # Volumetric flow rate, US gallons per hour, USGal/h
            '67':'V2',         # Volts squared, Volt squared (W2/A2), V2
            '104':'V2h',         # volt-squared hour, Volt-squared-hours, V2h
            '117':'VAhPerRev',         # Kh-Vah, apparent energy metering constant, VAh/rev
            '116':'VArhPerRev',         # Kh-VArh, reactive energy metering constant, VArh/rev
            '74':'VPerHz',         # Magnetic flux, Volts per Hertz, V/Hz
            '151':'VPerV',         # Voltage, Ratio of voltages (e.g. mV/V), V/V
            '66':'Vs',         # Volt seconds, Volt seconds (Ws/A), Vs
            '36':'wb',         # Magnetic flux, Weber (V s), Wb
            '107':'WhPerM3',         # Wh/m3, energy per volume, Wh/m3
            '115':'WhPerRev',         # Kh-Wh, active energy metering constant, Wh/rev
            '50':'wPerMK',         # Thermal conductivity, Watt/meter Kelvin, W/m K
            '81':'WPerSec',         # Ramp rate, Watts per second, W/s
            '153':'WPerVA',         # Power Factor, PF, W/VA
            '168':'WPerW',         # Signal Strength, Ratio of power, W/W
    };

def map_usage_kind(usage_kind_id):
    return usage_kind_map[usage_kind_id];

def map_reading_kind(reading_kind_id):
    return reading_kind_map[reading_kind_id];

def map_uom(uom):
    return uom_map[uom];
