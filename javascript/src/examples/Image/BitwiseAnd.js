// BitwiseAnd
//
// Extracts quality bits from MOD09GQ QC band, and masks pixels
// where the quality value is not "ideal".
// Lowest two bits contain quality value:
// 00: "produced at ideal quality all bands"
// 01: "produced at less than ideal quality some or all bands"
// 10: "not produced due to cloud effects all bands"
// 11: "not produced due to other reasons"

var modis = ee.Image('MOD09GQ/MOD09GQ_005_2012_02_08');
var qual = modis.select('QC_250m').bitwise_and(0x03).neq(0);

centerMap(-90.79994, 44.21912, 11);
addToMap(ee.Image([1, 0, 0]).mask(qual), {min: 0, max: 1},
         'quality_not_ideal');
addToMap(modis.select('sur_refl_b01').mask(qual.not()),
         {min: 100, max: 16000}, 'refl_b01');

