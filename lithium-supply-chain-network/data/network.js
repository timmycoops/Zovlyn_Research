/**
 * Lithium-Ion Battery Supply Chain — Network Data
 * ---------------------------------------------------------------
 * Source: Daniel Jimenez / iLiMarkets
 *   Adapted from the "Lithium-Ion Battery Supply Chain: equity and
 *   large financing relationships" map (snapshot: 7 May 2026).
 *
 * This file is the editable data layer. To add or correct an
 * entity or relationship, modify the arrays below — no other
 * file changes are required.
 *
 * NODE SCHEMA
 *   { id, name, role, country, stage, resource?, capacity_kt_lce? }
 *   role     : miner | refiner | cam | cell | oem | investor | oilgas | recycler
 *   stage    : production | project
 *   resource : hardrock | brine | clay   (optional, for miners)
 *   country  : ISO-2 code (drives flag rendering in index.html)
 *   capacity_kt_lce : OPTIONAL annual capacity in kilotonnes LCE-equivalent.
 *                     Universal unit so miners, refiners, and cell makers can
 *                     be compared on the same scale. Conventions:
 *                       miners/refiners — direct kt LCE/yr nameplate
 *                       cells           — GWh × 0.6  (LCE consumption)
 *                       cam             — kt cathode × ~0.4 (LCE content)
 *                     Drives node radius. Absent → minimum-size dot.
 *
 * LINK SCHEMA
 *   { source, target, type, stake? }
 *   type  : equity | financing | offtake
 *   stake : OPTIONAL number 0–1 representing source's ownership of target.
 *           Only meaningful for type === 'equity'. e.g. 0.225 = 22.5%.
 *           When present, edge thickness scales with stake; when absent
 *           the edge renders at default thickness with a "—" stake label.
 *
 * Both source and target must reference an existing node id.
 * Orphan references are filtered at runtime but kept clean here.
 */

const NODES = [
  // Western miners — hard rock
  { id: 'liontown',    name: 'Liontown',          role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 45, asset_match: 'Liontown Resources' },
  { id: 'pilbara',     name: 'Pilbara Minerals',  role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 110, asset_match: 'Pilbara Minerals' },
  { id: 'mineralres',  name: 'Mineral Resources', role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', asset_match: 'Mineral Resources' },
  { id: 'igo',         name: 'IGO',               role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', asset_match: 'IGO Limited' },
  { id: 'wesfarmers',  name: 'Wesfarmers',        role: 'investor', country: 'AU', stage: 'production' },
  { id: 'mtholland',   name: 'Mt Holland',        role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 25, asset_match: 'Mt Holland' },
  { id: 'wodgina',     name: 'Wodgina',           role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 70, asset_match: 'Wodgina' },
  { id: 'baldhill',    name: 'Bald Hill',         role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 0, asset_match: 'Bald Hill' },
  { id: 'mtmarion',    name: 'Mt Marion',         role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 56, asset_match: 'Mt Marion' },
  { id: 'mtcattlin',   name: 'Mt Cattlin',        role: 'miner',    country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 0, asset_match: 'Mt Cattlin' },
  { id: 'talison',     name: 'Talison (Greenbushes)', role: 'miner', country: 'AU', stage: 'production', resource: 'hardrock', capacity_kt_lce: 230, asset_match: 'Talison (Albemarle/Tianqi/IGO JV)' },
  { id: 'corelithium', name: 'Core Lithium',      role: 'miner',    country: 'AU', stage: 'project',    resource: 'hardrock', capacity_kt_lce: 8, asset_match: 'Core Lithium' },
  { id: 'delta',       name: 'Delta Lithium',     role: 'miner',    country: 'AU', stage: 'project',    resource: 'hardrock' },
  { id: 'azure',       name: 'Azure Minerals',    role: 'miner',    country: 'AU', stage: 'project',    resource: 'hardrock' },
  { id: 'wildcat',     name: 'WildCat',           role: 'miner',    country: 'AU', stage: 'project',    resource: 'hardrock' },
  { id: 'essential',   name: 'Essential M / Dome North', role: 'miner', country: 'AU', stage: 'project', resource: 'hardrock' },
  { id: 'norseman',    name: 'Norseman',          role: 'miner',    country: 'AU', stage: 'project',    resource: 'hardrock' },
  { id: 'newage',      name: 'New Age Metals',    role: 'miner',    country: 'CA', stage: 'project',    resource: 'hardrock' },
  { id: 'fmg',         name: 'FMG',               role: 'investor', country: 'AU', stage: 'production' },
  { id: 'hancock',     name: 'Hancock Prospecting', role: 'investor', country: 'AU', stage: 'production' },
  { id: 'rio',         name: 'Rio Tinto',         role: 'miner',    country: 'UK', stage: 'production', asset_match: 'Rio Tinto (ex-Arcadium)' },

  // South American brine
  { id: 'sqm',         name: 'SQM',               role: 'miner',    country: 'CL', stage: 'production', resource: 'brine', capacity_kt_lce: 210, asset_match: 'SQM' },
  { id: 'albemarle',   name: 'Albemarle',         role: 'refiner',  country: 'US', stage: 'production', capacity_kt_lce: 50, asset_match: 'Albemarle' },
  { id: 'atacama',     name: 'Atacama',           role: 'miner',    country: 'CL', stage: 'production', resource: 'brine', capacity_kt_lce: 240, asset_match: 'Salar de Atacama' },
  { id: 'olaroz',      name: 'Olaroz',            role: 'miner',    country: 'AR', stage: 'production', resource: 'brine', capacity_kt_lce: 30, asset_match: 'Olaroz' },
  { id: 'salvida',     name: 'Sal de Vida',       role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine', capacity_kt_lce: 5, asset_match: 'Sal de Vida' },
  { id: 'fenix',       name: 'Fenix (Hombre Muerto)', role: 'miner', country: 'AR', stage: 'production', resource: 'brine', capacity_kt_lce: 22, asset_match: 'Fénix' },
  { id: 'rincon',      name: 'Rincon',            role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'cauchari',    name: 'Cauchari-Olaroz',   role: 'miner',    country: 'AR', stage: 'production', resource: 'brine', capacity_kt_lce: 40 },
  { id: 'mariana',     name: 'Mariana / Llullaillaco', role: 'miner', country: 'AR', stage: 'project',  resource: 'brine' },
  { id: 'maricunga',   name: 'Maricunga',         role: 'miner',    country: 'CL', stage: 'project',    resource: 'brine' },
  { id: 'salaroz',     name: 'Sal de Oro',        role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'pastosgrandes', name: '3Q (Pastos Grandes)', role: 'miner', country: 'AR', stage: 'project',  resource: 'brine' },
  { id: 'galan',       name: 'Galan / HMW',       role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'salinas',     name: 'Salinas',           role: 'miner',    country: 'BR', stage: 'project',    resource: 'brine' },
  { id: 'goulamina',   name: 'Goulamina',         role: 'miner',    country: 'ML', stage: 'project',    resource: 'hardrock', capacity_kt_lce: 60, asset_match: 'Goulamina' },
  { id: 'arcadia',     name: 'Arcadia',           role: 'miner',    country: 'ZW', stage: 'production', resource: 'hardrock', capacity_kt_lce: 53, asset_match: 'Arcadia' },
  { id: 'kamativi',    name: 'Kamativi',          role: 'miner',    country: 'ZW', stage: 'project',    resource: 'hardrock' },
  { id: 'bikita',      name: 'Bikita',            role: 'miner',    country: 'ZW', stage: 'production', resource: 'hardrock', capacity_kt_lce: 45, asset_match: 'Bikita' },
  { id: 'sabistar',    name: 'SabiStar Li',       role: 'miner',    country: 'ZW', stage: 'project',    resource: 'hardrock' },
  { id: 'zulu',        name: 'Zulu / Premier Af Min', role: 'miner', country: 'ZW', stage: 'project', resource: 'hardrock' },
  { id: 'codelco',     name: 'Codelco',           role: 'investor', country: 'CL', stage: 'production' },
  { id: 'enami',       name: 'Enami',             role: 'investor', country: 'CL', stage: 'production' },
  { id: 'ratones',     name: 'Ratones Centenario', role: 'miner',   country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'argentlith',  name: 'Argentina Lithium', role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'lithargentina', name: 'Lithium Argentina', role: 'miner',  country: 'AR', stage: 'production', resource: 'brine' },
  { id: 'lithamericas',name: 'Lithium Americas',  role: 'miner',    country: 'US', stage: 'production' },
  { id: 'sigma',       name: 'Sigma',             role: 'miner',    country: 'BR', stage: 'production', resource: 'hardrock', capacity_kt_lce: 40, asset_match: 'Sigma Lithium' },
  { id: 'amg',         name: 'AMG',               role: 'miner',    country: 'BR', stage: 'production', resource: 'hardrock' },
  { id: 'lithionic',   name: 'Lithium Ionic',     role: 'miner',    country: 'BR', stage: 'project',    resource: 'hardrock' },

  // Chinese refiners & integrated
  { id: 'tianqi',      name: 'Tianqi',            role: 'refiner',  country: 'CN', stage: 'production', capacity_kt_lce: 24, asset_match: 'Tianqi Lithium' },
  { id: 'ganfeng',     name: 'Ganfeng',           role: 'refiner',  country: 'CN', stage: 'production', capacity_kt_lce: 250, asset_match: 'Ganfeng Lithium' },
  { id: 'yahua',       name: 'Yahua',             role: 'refiner',  country: 'CN', stage: 'production', capacity_kt_lce: 70 },
  { id: 'chengxin',    name: 'Chengxin',          role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'yibin',       name: 'Yibin Tianyi',      role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'ruifu',       name: 'Ruifu',             role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'sichuanlij',  name: 'Sichuan Lijiagou',  role: 'miner',    country: 'CN', stage: 'production', resource: 'hardrock' },
  { id: 'ningdu',      name: 'Ningdu Jiangxi',    role: 'miner',    country: 'CN', stage: 'production', resource: 'hardrock' },
  { id: 'yichun',      name: 'Yichun',            role: 'miner',    country: 'CN', stage: 'production', resource: 'hardrock' },
  { id: 'zhabuye',     name: 'Zhabuye Tibet',     role: 'miner',    country: 'CN', stage: 'production', resource: 'brine' },
  { id: 'qinghaisalt', name: 'Qinghai Salt Lake', role: 'miner',    country: 'CN', stage: 'production', resource: 'brine' },
  { id: 'cuola',       name: 'Cuola Sichuan',     role: 'miner',    country: 'CN', stage: 'project',    resource: 'hardrock' },
  { id: 'dynanonics',  name: 'Dynanonics',        role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'jvlfp',       name: 'JV LFP',            role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'huayou',      name: 'Huayou Cobalt',     role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'zijin',       name: 'Zijin Mining',      role: 'miner',    country: 'CN', stage: 'production' },
  { id: 'xiangyuan',   name: 'Xiangyuan',         role: 'miner',    country: 'CN', stage: 'production' },
  { id: 'zangee',      name: 'Zangee',            role: 'miner',    country: 'CN', stage: 'production' },
  { id: 'lakkortso',   name: 'Lakkor Tso',        role: 'miner',    country: 'CN', stage: 'project',    resource: 'brine' },
  { id: 'manono',      name: 'Manono Lithium',    role: 'miner',    country: 'CD', stage: 'project',    resource: 'hardrock' },
  { id: 'manono22',    name: 'Manono 2/2',        role: 'miner',    country: 'CD', stage: 'project',    resource: 'hardrock' },
  { id: 'brump',       name: 'Brump',             role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'sinowei',     name: 'Sinowei',           role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'cath',        name: 'CATH',              role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'canmax',      name: 'Canmax',            role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'jvgfgpls',    name: 'JV GFG-PLS',        role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'jianziawo',   name: 'Jianziawo',         role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'songshugang', name: 'Songshugang Shangrao', role: 'refiner', country: 'CN', stage: 'production' },
  { id: 'yelonggou',   name: 'Yelonggou Sichuan', role: 'miner',    country: 'CN', stage: 'production', resource: 'hardrock' },
  { id: 'yilping',     name: 'Yilping Qinghai',   role: 'miner',    country: 'CN', stage: 'production', resource: 'brine' },
  { id: 'murong',      name: 'Murong Sichuan',    role: 'miner',    country: 'CN', stage: 'project',    resource: 'hardrock' },
  { id: 'hunanyongshan', name: 'Hunan Yongshan', role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'easpring',    name: 'Easpring',          role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'kotka',       name: 'Kotka CAM',         role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'cngr',        name: 'CNGR',              role: 'cam',      country: 'CN', stage: 'production' },
  { id: 'xinhua',      name: 'Xinhua Lithium',    role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'jinkunlun',   name: 'Jinkunlun',         role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'dahua',       name: 'Dahua',             role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'wmc',         name: 'WMC',               role: 'refiner',  country: 'US', stage: 'project' },
  { id: 'sinomine',    name: 'Sinomine',          role: 'miner',    country: 'CN', stage: 'production' },
  { id: 'tsingshan',   name: 'Tsingshan',         role: 'investor', country: 'CN', stage: 'production' },
  { id: 'minmetal',    name: 'Minmetal',          role: 'investor', country: 'CN', stage: 'production' },
  { id: 'dongpeng',    name: 'Dongpeng',          role: 'miner',    country: 'CN', stage: 'project' },
  { id: 'hainan',      name: 'Hainan',            role: 'refiner',  country: 'CN', stage: 'production' },
  { id: 'indonesia',   name: 'Indonesia HPAL',    role: 'refiner',  country: 'ID', stage: 'production' },
  { id: 'vilasto',     name: 'Vilasto / Inner Mongolia', role: 'miner', country: 'CN', stage: 'project' },
  { id: 'jama',        name: 'Jama',              role: 'miner',    country: 'CN', stage: 'project' },
  { id: 'solaroz',     name: 'Solaroz',           role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'bacanora',    name: 'Bacanora',          role: 'miner',    country: 'MX', stage: 'project',    resource: 'clay' },
  { id: 'qinghaisalt2', name: 'Qinghai Salt Lake 2', role: 'miner', country: 'CN', stage: 'production', resource: 'brine' },

  // Cell producers
  { id: 'catl',        name: 'CATL',              role: 'cell',     country: 'CN', stage: 'production', capacity_kt_lce: 360 },
  { id: 'byd',         name: 'BYD',               role: 'cell',     country: 'CN', stage: 'production', capacity_kt_lce: 240 },
  { id: 'lgchem',      name: 'LG Chem',           role: 'cell',     country: 'KR', stage: 'production', capacity_kt_lce: 240 },
  { id: 'sk',          name: 'SK',                role: 'cell',     country: 'KR', stage: 'production', capacity_kt_lce: 90 },
  { id: 'svolt',       name: 'SVolt',             role: 'cell',     country: 'CN', stage: 'production', capacity_kt_lce: 30 },
  { id: 'eve',         name: 'Eve',               role: 'cell',     country: 'CN', stage: 'production', capacity_kt_lce: 60 },
  { id: 'posco',       name: 'POSCO',             role: 'cam',      country: 'KR', stage: 'production' },
  { id: 'gwangyang',   name: 'Gwangyang',         role: 'cam',      country: 'KR', stage: 'production' },
  { id: 'basf',        name: 'BASF Shanshan',     role: 'cam',      country: 'DE', stage: 'production' },
  { id: 'ecopro',      name: 'Ecopro',            role: 'cam',      country: 'KR', stage: 'production' },

  // OEMs
  { id: 'ford',        name: 'Ford',              role: 'oem',      country: 'US', stage: 'production' },
  { id: 'gm',          name: 'GM',                role: 'oem',      country: 'US', stage: 'production' },
  { id: 'stellantis',  name: 'Stellantis',        role: 'oem',      country: 'FR', stage: 'production' },
  { id: 'vw',          name: 'VW',                role: 'oem',      country: 'DE', stage: 'production' },
  { id: 'toyota',      name: 'Toyota TC',         role: 'oem',      country: 'JP', stage: 'production' },
  { id: 'nio',         name: 'Nio',               role: 'oem',      country: 'CN', stage: 'production' },
  { id: 'greatwall',   name: 'Great Wall',        role: 'oem',      country: 'CN', stage: 'production' },
  { id: 'smart',       name: 'Smart',             role: 'oem',      country: 'DE', stage: 'production' },
  { id: 'pmt',         name: 'PMT',               role: 'oem',      country: 'CA', stage: 'project' },

  // Other miners (Canadian, European)
  { id: 'sayona',      name: 'Sayona / Piedmont', role: 'miner',    country: 'CA', stage: 'production', resource: 'hardrock' },
  { id: 'nal',         name: 'NAL',               role: 'miner',    country: 'CA', stage: 'production', resource: 'hardrock' },
  { id: 'piedmont',    name: 'Piedmont',          role: 'miner',    country: 'US', stage: 'project',    resource: 'hardrock' },
  { id: 'nemaska',     name: 'Nemaska',           role: 'miner',    country: 'CA', stage: 'project',    resource: 'hardrock' },
  { id: 'jamesbay',    name: 'James Bay',         role: 'miner',    country: 'CA', stage: 'project',    resource: 'hardrock' },
  { id: 'nanoone',     name: 'nanoOne',           role: 'cam',      country: 'CA', stage: 'project' },
  { id: 'aterian',     name: 'Aterian',           role: 'miner',    country: 'CA', stage: 'project' },
  { id: 'frontier',    name: 'Frontier Li',       role: 'miner',    country: 'CA', stage: 'project',    resource: 'hardrock' },
  { id: 'rocktech',    name: 'Rock Tech',         role: 'refiner',  country: 'CA', stage: 'project' },
  { id: 'greenlith',   name: 'Green Lithium',     role: 'refiner',  country: 'UK', stage: 'project' },
  { id: 'standardli',  name: 'Standard Lithium',  role: 'miner',    country: 'US', stage: 'project',    resource: 'brine' },
  { id: 'arkansas',    name: 'Arkansas SWA',      role: 'miner',    country: 'US', stage: 'project',    resource: 'brine' },
  { id: 'e3',          name: 'E3 Lithium',        role: 'miner',    country: 'CA', stage: 'project',    resource: 'brine' },
  { id: 'pureenergy',  name: 'Pure Energy',       role: 'miner',    country: 'US', stage: 'project',    resource: 'brine' },
  { id: 'controlth',   name: 'Controlled Thermal R.', role: 'miner', country: 'US', stage: 'project',  resource: 'brine' },
  { id: 'ioneer',      name: 'Ioneer',            role: 'miner',    country: 'US', stage: 'project',    resource: 'clay' },
  { id: 'thackerpass', name: 'Thacker Pass',      role: 'miner',    country: 'US', stage: 'project',    resource: 'clay' },
  { id: 'lakeresources',name: 'Lake Resources',   role: 'miner',    country: 'AU', stage: 'project',    resource: 'brine' },
  { id: 'vulcan',      name: 'Vulcan Energy',     role: 'miner',    country: 'DE', stage: 'project',    resource: 'brine' },
  { id: 'zinnwald',    name: 'Zinnwald',          role: 'miner',    country: 'DE', stage: 'project',    resource: 'hardrock' },
  { id: 'savannah',    name: 'Savannah',          role: 'miner',    country: 'PT', stage: 'project',    resource: 'hardrock' },
  { id: 'keliber',     name: 'Keliber',           role: 'miner',    country: 'FI', stage: 'project',    resource: 'hardrock' },
  { id: 'ioncor',      name: 'Ioncor',            role: 'cell',     country: 'FI', stage: 'project' },
  { id: 'sibanye',     name: 'Sibanye Stillwater', role: 'investor', country: 'ZA', stage: 'production' },
  { id: 'weardale',    name: 'Weardale Lithium',  role: 'miner',    country: 'UK', stage: 'project',    resource: 'brine' },
  { id: 'teesvalley',  name: 'Tees Valley',       role: 'refiner',  country: 'UK', stage: 'project' },
  { id: 'jadar',       name: 'Jadar',             role: 'miner',    country: 'RS', stage: 'project',    resource: 'hardrock' },
  { id: 'icl',         name: 'ICL',               role: 'refiner',  country: 'IL', stage: 'production' },
  { id: 'andrada',     name: 'Andrada',           role: 'miner',    country: 'NA', stage: 'project',    resource: 'hardrock' },
  { id: 'kodal',       name: 'Kodal Bougouni',    role: 'miner',    country: 'ML', stage: 'project',    resource: 'hardrock' },
  { id: 'ewoyaa',      name: 'Ewoyaa',            role: 'miner',    country: 'GH', stage: 'project',    resource: 'hardrock' },
  { id: 'novaandino',  name: 'NovaAndino',        role: 'miner',    country: 'PE', stage: 'project',    resource: 'hardrock' },
  { id: 'atlas',       name: 'Atlas Lithium',     role: 'miner',    country: 'BR', stage: 'project',    resource: 'hardrock' },
  { id: 'altos',       name: 'Altos Andinos',     role: 'miner',    country: 'CL', stage: 'project',    resource: 'brine' },
  { id: 'diabllos',    name: 'Diablillos',        role: 'miner',    country: 'AR', stage: 'project' },
  { id: 'ppg',         name: 'PPG',               role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'licentury',   name: 'Li Century',        role: 'miner',    country: 'CA', stage: 'project' },
  { id: 'tanco',       name: 'Tanco',             role: 'miner',    country: 'CA', stage: 'production', resource: 'hardrock' },
  { id: 'aquatech',    name: 'Aquatech (KTS)',    role: 'refiner',  country: 'US', stage: 'project' },
  { id: 'eramet',      name: 'Eramet',            role: 'miner',    country: 'FR', stage: 'project' },
  { id: 'equinor',     name: 'Equinor',           role: 'oilgas',   country: 'NO', stage: 'production' },

  // Investors / Traders / Oil & Gas
  { id: 'mitsui',      name: 'Mitsui',            role: 'investor', country: 'JP', stage: 'production' },
  { id: 'mitsubishi',  name: 'Mitsubishi',        role: 'investor', country: 'JP', stage: 'production' },
  { id: 'glencore',    name: 'Glencore',          role: 'investor', country: 'CH', stage: 'production' },
  { id: 'trafigura',   name: 'Trafigura',         role: 'investor', country: 'CH', stage: 'production' },
  { id: 'transamine',  name: 'Transamine',        role: 'investor', country: 'CH', stage: 'production' },
  { id: 'traxys',      name: 'Traxys',            role: 'investor', country: 'CH', stage: 'production' },
  { id: 'kobold',      name: 'Kobold Metals',     role: 'investor', country: 'US', stage: 'project' },
  { id: 'glr',         name: 'GLR',               role: 'investor', country: 'AU', stage: 'project' },
  { id: 'bcm',         name: 'BCM',               role: 'investor', country: 'CN', stage: 'production' },
  { id: 'exxon',       name: 'Exxon',             role: 'oilgas',   country: 'US', stage: 'project' },
  { id: 'schlumberger',name: 'Schlumberger',      role: 'oilgas',   country: 'US', stage: 'project' },
  { id: 'legacysaga',  name: 'Legacy / Saga',     role: 'oilgas',   country: 'CA', stage: 'project' },
  { id: 'mineralres2', name: 'Mineral Resources (Brazil)', role: 'investor', country: 'BR', stage: 'production' },
  { id: 'igo2',        name: 'IGO Equity',        role: 'investor', country: 'AU', stage: 'production' },

  // Recyclers
  { id: 'licycle',     name: 'Li-Cycle',          role: 'recycler', country: 'CA', stage: 'production' },
  { id: 'lithionr',    name: 'Lithion Recycling', role: 'recycler', country: 'CA', stage: 'project' },

  // Mitsui-related & other
  { id: 'mitsui2',     name: 'Mitsui (Equity)',   role: 'investor', country: 'JP', stage: 'production' },
  { id: 'wodgina2',    name: 'Wodgina (Wesfarmers)', role: 'miner', country: 'AU', stage: 'production' },
  { id: 'qinghaisalt3',name: 'Qinghai Salt Lake (CN)', role: 'miner', country: 'CN', stage: 'production', resource: 'brine' },
  { id: 'tesla',       name: 'Tesla',             role: 'oem',      country: 'US', stage: 'production' },
  { id: 'kemerton',    name: 'Kemerton',          role: 'refiner',  country: 'AU', stage: 'production', capacity_kt_lce: 0, asset_match: 'Kemerton' },
  { id: 'allkem',      name: 'Allkem',            role: 'miner',    country: 'AR', stage: 'production', resource: 'brine' },
  { id: 'greenwing',   name: 'Greenwing',         role: 'miner',    country: 'AR', stage: 'project',    resource: 'brine' },
  { id: 'sonora',      name: 'Sonora',            role: 'miner',    country: 'MX', stage: 'project',    resource: 'clay' },
  { id: 'avalon',      name: 'Avalon',            role: 'miner',    country: 'CA', stage: 'project',    resource: 'hardrock' }
];

// Relationships — source, target, type (equity/financing/offtake)
const LINKS = [
  // Albemarle-Tianqi-IGO-Talison cluster (Greenbushes)
  // Talison is held 51% by TLEA / 49% Albemarle direct.
  // TLEA is in turn 51% Tianqi / 49% IGO. Stakes shown here are direct.
  { source: 'igo',        target: 'talison',    type: 'equity', stake: 0.25 }, // 49% × 51% effective
  { source: 'tianqi',     target: 'talison',    type: 'equity', stake: 0.26 }, // 51% × 51% effective
  { source: 'albemarle',  target: 'talison',    type: 'equity', stake: 0.49 },
  { source: 'igo',        target: 'tianqi',     type: 'equity', stake: 0.49 }, // IGO's stake in TLEA
  { source: 'tianqi',     target: 'sqm',        type: 'equity', stake: 0.22 }, // SQM-B shares
  { source: 'tianqi',     target: 'liontown',   type: 'equity' },
  { source: 'tianqi',     target: 'dynanonics', type: 'equity' },
  { source: 'tianqi',     target: 'jvlfp',      type: 'equity' },

  // Albemarle holdings
  { source: 'albemarle',  target: 'wodgina',    type: 'equity', stake: 0.50 }, // 50/50 JV with MinRes
  { source: 'albemarle',  target: 'atacama',    type: 'equity' },
  { source: 'albemarle',  target: 'lithamericas', type: 'equity' },
  { source: 'albemarle',  target: 'kemerton',   type: 'equity', stake: 0.60 }, // 60/40 JV with MinRes

  // SQM holdings
  { source: 'sqm',        target: 'atacama',    type: 'equity' },
  { source: 'sqm',        target: 'mtholland',  type: 'equity', stake: 0.50 }, // Covalent JV
  { source: 'sqm',        target: 'codelco',    type: 'equity' },
  { source: 'sqm',        target: 'andrada',    type: 'equity' },
  { source: 'codelco',    target: 'maricunga',  type: 'equity' },
  { source: 'codelco',    target: 'salaroz',    type: 'equity' },

  // Liontown
  { source: 'liontown',   target: 'ford',       type: 'offtake' },
  { source: 'liontown',   target: 'lgchem',     type: 'offtake' },
  { source: 'liontown',   target: 'tesla',      type: 'offtake' },

  // Mineral Resources / Hancock / IGO
  { source: 'mineralres', target: 'wodgina',    type: 'equity', stake: 0.50 }, // 50/50 with Albemarle
  { source: 'mineralres', target: 'mtmarion',   type: 'equity', stake: 0.50 }, // 50/50 with Ganfeng
  { source: 'mineralres', target: 'baldhill',   type: 'equity', stake: 1.00 }, // 100%
  { source: 'wesfarmers', target: 'mtholland',  type: 'equity', stake: 0.50 }, // Covalent JV
  { source: 'igo',        target: 'mtholland',  type: 'equity' },
  { source: 'hancock',    target: 'azure',      type: 'equity' },
  { source: 'hancock',    target: 'liontown',   type: 'equity', stake: 0.20 }, // ~19.9% blocking stake
  { source: 'hancock',    target: 'delta',      type: 'equity' },

  // Pilbara
  { source: 'pilbara',    target: 'ganfeng',    type: 'offtake' },
  { source: 'pilbara',    target: 'posco',      type: 'equity' },
  { source: 'pilbara',    target: 'salaroz',    type: 'equity' },
  { source: 'pilbara',    target: 'jvgfgpls',   type: 'equity' },

  // Ganfeng global (large investor in many)
  { source: 'ganfeng',    target: 'cauchari',   type: 'equity', stake: 0.45 }, // 44.8% via JV with Lithium Argentina
  { source: 'ganfeng',    target: 'mariana',    type: 'equity', stake: 1.00 }, // 100%
  { source: 'ganfeng',    target: 'goulamina',  type: 'equity', stake: 1.00 }, // 100% post Leo Lithium buyout
  { source: 'ganfeng',    target: 'rincon',     type: 'equity' },
  { source: 'ganfeng',    target: 'bacanora',   type: 'equity' },
  { source: 'ganfeng',    target: 'corelithium',type: 'equity' },
  { source: 'ganfeng',    target: 'sonora',     type: 'equity' },
  { source: 'ganfeng',    target: 'avalon',     type: 'equity' },
  { source: 'ganfeng',    target: 'lithamericas', type: 'financing' },
  { source: 'ganfeng',    target: 'sichuanlij', type: 'equity' },
  { source: 'ganfeng',    target: 'pilbara',    type: 'equity' },
  { source: 'ganfeng',    target: 'argentlith', type: 'equity' },
  { source: 'ganfeng',    target: 'jamesbay',   type: 'equity' },

  // CATL global
  { source: 'catl',       target: 'manono',     type: 'equity' },
  { source: 'catl',       target: 'jianziawo',  type: 'equity' },
  { source: 'catl',       target: 'pilbara',    type: 'equity' },
  { source: 'catl',       target: 'kamativi',   type: 'equity' },
  { source: 'catl',       target: 'cath',       type: 'equity' },
  { source: 'catl',       target: 'brump',      type: 'equity' },
  { source: 'catl',       target: 'yibin',      type: 'equity' },
  { source: 'catl',       target: 'ningdu',     type: 'equity' },
  { source: 'catl',       target: 'eve',        type: 'equity' },

  // BYD
  { source: 'byd',        target: 'sichuanlij', type: 'equity' },
  { source: 'byd',        target: 'qinghaisalt',type: 'equity' },
  { source: 'byd',        target: 'huayou',     type: 'equity' },
  { source: 'byd',        target: 'zangee',     type: 'equity' },
  { source: 'byd',        target: 'arcadia',    type: 'equity' },
  { source: 'byd',        target: 'manono22',   type: 'equity' },
  { source: 'byd',        target: 'chengxin',   type: 'equity' },

  // Yahua
  { source: 'yahua',      target: 'mtmarion',   type: 'offtake' },
  { source: 'yahua',      target: 'tesla',      type: 'offtake' },
  { source: 'yahua',      target: 'corelithium',type: 'offtake' },
  { source: 'yahua',      target: 'pilbara',    type: 'offtake' },
  { source: 'yahua',      target: 'kamativi',   type: 'equity' },

  // Chengxin
  { source: 'chengxin',   target: 'sabistar',   type: 'equity' },
  { source: 'chengxin',   target: 'huayou',     type: 'equity' },
  { source: 'chengxin',   target: 'wodgina',    type: 'equity' },
  { source: 'chengxin',   target: 'ewoyaa',     type: 'equity' },
  { source: 'chengxin',   target: 'murong',     type: 'equity' },

  // Huayou
  { source: 'huayou',     target: 'arcadia',    type: 'equity' },
  { source: 'huayou',     target: 'yibin',      type: 'equity' },
  { source: 'huayou',     target: 'cngr',       type: 'equity' },

  // Zijin
  { source: 'zijin',      target: 'zangee',     type: 'equity' },
  { source: 'zijin',      target: 'lakkortso',  type: 'equity' },
  { source: 'zijin',      target: 'xiangyuan',  type: 'equity' },
  { source: 'zijin',      target: 'pastosgrandes',         type: 'equity' },

  // POSCO
  { source: 'posco',      target: 'salaroz',    type: 'equity' },
  { source: 'posco',      target: 'pilbara',    type: 'equity' },
  { source: 'posco',      target: 'gwangyang',  type: 'equity' },
  { source: 'posco',      target: 'ecopro',     type: 'equity' },

  // LG Chem
  { source: 'lgchem',     target: 'sayona',     type: 'offtake' },
  { source: 'lgchem',     target: 'piedmont',   type: 'offtake' },
  { source: 'lgchem',     target: 'liontown',   type: 'offtake' },
  { source: 'lgchem',     target: 'kemerton',   type: 'offtake' },

  // Mitsui / Mitsubishi
  { source: 'mitsui',     target: 'salvida',    type: 'equity' },
  { source: 'mitsui',     target: 'olaroz',     type: 'equity' },
  { source: 'mitsui',     target: 'atlas',      type: 'equity' },
  { source: 'mitsubishi', target: 'fenix',      type: 'equity' },
  { source: 'mitsubishi', target: 'eramet',     type: 'equity' },

  // Glencore / Trafigura
  { source: 'glencore',   target: 'licycle',    type: 'equity' },
  { source: 'glencore',   target: 'arcadia',    type: 'offtake' },
  { source: 'trafigura',  target: 'enami',      type: 'financing' },
  { source: 'trafigura',  target: 'greenlith',  type: 'financing' },
  { source: 'transamine', target: 'rocktech',   type: 'offtake' },
  { source: 'traxys',     target: 'aquatech',   type: 'financing' },

  // OEMs
  { source: 'ford',       target: 'liontown',   type: 'offtake' },
  { source: 'ford',       target: 'ioneer',     type: 'offtake' },
  { source: 'ford',       target: 'lithamericas',type: 'equity' },
  { source: 'gm',         target: 'lithamericas', type: 'equity' },
  { source: 'gm',         target: 'controlth',  type: 'equity' },
  { source: 'gm',         target: 'pmt',        type: 'offtake' },
  { source: 'stellantis', target: 'controlth',  type: 'offtake' },
  { source: 'stellantis', target: 'vulcan',     type: 'equity' },
  { source: 'stellantis', target: 'argentlith', type: 'equity' },
  { source: 'vw',         target: 'svolt',      type: 'offtake' },
  { source: 'vw',         target: 'ganfeng',    type: 'offtake' },
  { source: 'toyota',     target: 'olaroz',     type: 'equity' },
  { source: 'toyota',     target: 'salvida',    type: 'equity' },
  { source: 'toyota',     target: 'rincon',     type: 'equity' },
  { source: 'nio',        target: 'greenwing',  type: 'equity' },
  { source: 'nio',        target: 'huayou',     type: 'equity' },
  { source: 'greatwall',  target: 'pilbara',    type: 'equity' },
  { source: 'greatwall',  target: 'svolt',      type: 'equity' },
  { source: 'smart',      target: 'liontown',   type: 'offtake' },

  // Rio Tinto
  { source: 'rio',        target: 'jadar',      type: 'equity' },
  { source: 'rio',        target: 'rincon',     type: 'equity' },
  { source: 'rio',        target: 'arkansas',   type: 'equity' },
  { source: 'rio',        target: 'olaroz',     type: 'equity' },
  { source: 'rio',        target: 'fenix',      type: 'equity' },

  // FMG
  { source: 'fmg',        target: 'altos',      type: 'equity' },
  { source: 'fmg',        target: 'novaandino', type: 'equity' },

  // Oil & Gas
  { source: 'exxon',      target: 'arkansas',   type: 'equity' },
  { source: 'exxon',      target: 'standardli', type: 'equity' },
  { source: 'equinor',    target: 'standardli', type: 'equity' },
  { source: 'schlumberger', target: 'pureenergy', type: 'equity' },
  { source: 'legacysaga', target: 'e3',         type: 'equity' },

  // Sayona / Piedmont / NAL
  { source: 'piedmont',   target: 'sayona',     type: 'equity' },
  { source: 'piedmont',   target: 'nal',        type: 'equity' },
  { source: 'piedmont',   target: 'ewoyaa',     type: 'equity' },
  { source: 'sayona',     target: 'nal',        type: 'equity' },

  // Kobold
  { source: 'kobold',     target: 'manono',     type: 'equity' },

  // Posco / BASF / CAM
  { source: 'basf',       target: 'easpring',   type: 'equity' },
  { source: 'basf',       target: 'kotka',      type: 'equity' },

  // Sibanye
  { source: 'sibanye',    target: 'keliber',    type: 'equity' },
  { source: 'sibanye',    target: 'ioncor',     type: 'equity' },
  { source: 'sibanye',    target: 'ioneer',     type: 'equity' },

  // Eve
  { source: 'eve',        target: 'songshugang',type: 'equity' },

  // SVolt
  { source: 'svolt',      target: 'mariana',    type: 'equity' },
  { source: 'svolt',      target: 'hunanyongshan', type: 'equity' },

  // CNGR
  { source: 'cngr',       target: 'jinkunlun',  type: 'equity' },
  { source: 'cngr',       target: 'xinhua',     type: 'equity' },
  { source: 'cngr',       target: 'wmc',        type: 'equity' },

  // SK
  { source: 'sk',         target: 'lakeresources', type: 'offtake' },

  // Vulcan
  { source: 'vulcan',     target: 'pilbara',    type: 'offtake' },

  // Tsingshan
  { source: 'tsingshan',  target: 'indonesia',  type: 'equity' },
  { source: 'tsingshan',  target: 'hainan',     type: 'equity' },
  { source: 'tsingshan',  target: 'goulamina',  type: 'equity' },

  // Minmetal
  { source: 'minmetal',   target: 'tanco',      type: 'equity' },
  { source: 'minmetal',   target: 'frontier',   type: 'equity' },

  // ICL
  { source: 'icl',        target: 'qinghaisalt',type: 'equity' },

  // Other small connections from chart
  { source: 'wesfarmers', target: 'kemerton',   type: 'equity' },
  { source: 'mineralres', target: 'baldhill',   type: 'equity' },
  { source: 'wildcat',    target: 'tianqi',     type: 'equity' },
  { source: 'newage',     target: 'wildcat',    type: 'equity' },
  { source: 'ningdu',     target: 'cuola',      type: 'equity' },
  { source: 'qinghaisalt',target: 'yilping',    type: 'equity' },
  { source: 'yichun',     target: 'ganfeng',    type: 'equity' },
  { source: 'sinomine',   target: 'bikita',     type: 'equity' },
  { source: 'sinomine',   target: 'zulu',       type: 'equity' },
  { source: 'sinomine',   target: 'tanco',      type: 'equity' },
  { source: 'canmax',     target: 'sabistar',   type: 'equity' },
  { source: 'canmax',     target: 'lithamericas', type: 'equity' },
  { source: 'jvgfgpls',   target: 'pilbara',    type: 'equity' },
  { source: 'jianziawo',  target: 'pilbara',    type: 'offtake' },
  { source: 'salinas',    target: 'sigma',      type: 'equity' },
  { source: 'lithargentina', target: 'cauchari',type: 'equity' },
  { source: 'lithargentina', target: 'salvida', type: 'equity' },
  { source: 'aquatech',   target: 'standardli', type: 'equity' },
  { source: 'lithionr',   target: 'glencore',   type: 'equity' },
  { source: 'enami',      target: 'salaroz',    type: 'equity' },
  { source: 'kodal',      target: 'hainan',     type: 'equity' },
  { source: 'ioneer',     target: 'thackerpass',type: 'equity' },
  { source: 'standardli', target: 'arkansas',   type: 'equity' },
  { source: 'glr',        target: 'manono',     type: 'equity' },
  { source: 'bcm',        target: 'manono',     type: 'equity' },
  { source: 'bcm',        target: 'qinghaisalt',type: 'equity' },
  { source: 'mariana',    target: 'salinas',    type: 'equity' },
  { source: 'svolt',      target: 'sinowei',    type: 'equity' },
  { source: 'cath',       target: 'salinas',    type: 'equity' },
  { source: 'eve',        target: 'argentlith', type: 'equity' },
  { source: 'mineralres2',target: 'sigma',      type: 'equity' },
  { source: 'igo2',       target: 'pilbara',    type: 'equity' },
  { source: 'lakkortso',  target: 'manono',     type: 'equity' },
  { source: 'qinghaisalt2', target: 'yelonggou', type: 'equity' },
  { source: 'sichuanlij', target: 'jvlfp',      type: 'equity' },
  { source: 'manono22',   target: 'manono',     type: 'equity' },
  { source: 'jinkunlun',  target: 'qinghaisalt',type: 'equity' },
  { source: 'xinhua',     target: 'qinghaisalt',type: 'equity' },
  { source: 'dahua',      target: 'qinghaisalt',type: 'equity' },
  { source: 'pmt',        target: 'jamesbay',   type: 'equity' },
  { source: 'jamesbay',   target: 'allkem',     type: 'equity' },
  { source: 'salaroz',    target: 'maricunga',  type: 'equity' },
  { source: 'gwangyang',  target: 'salaroz',    type: 'equity' },
  { source: 'controlth',  target: 'gm',         type: 'offtake' },
  { source: 'lithargentina', target: 'pastosgrandes', type: 'equity' }
];

// Expose to the global scope so index.html can consume it
window.LITHIUM_NETWORK = { nodes: NODES, links: LINKS };
