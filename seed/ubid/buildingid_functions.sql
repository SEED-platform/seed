-- Unique Building Identifier (UBID)
--
-- Copyright (c) 2022, Battelle Memorial Institute
-- All rights reserved.
--
-- 1. Battelle Memorial Institute (hereinafter Battelle) hereby grants permission
--    to any person or entity lawfully obtaining a copy of this software and
--    associated documentation files (hereinafter "the Software") to redistribute
--    and use the Software in source and binary forms, with or without
--    modification.  Such person or entity may use, copy, modify, merge, publish,
--    distribute, sublicense, and/or sell copies of the Software, and may permit
--    others to do so, subject to the following conditions:
--
--    * Redistributions of source code must retain the above copyright notice, this
--      list of conditions and the following disclaimers.
--    * Redistributions in binary form must reproduce the above copyright notice,
--      this list of conditions and the following disclaimer in the documentation
--      and/or other materials provided with the distribution.
--    * Other than as used herein, neither the name Battelle Memorial Institute or
--      Battelle may be used in any form whatsoever without the express written
--      consent of Battelle.
--
-- 2. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
-- AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
-- IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
-- DISCLAIMED. IN NO EVENT SHALL BATTELLE OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
-- INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
-- BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
-- DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
-- LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
-- OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
-- ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.



-- This material was prepared as an account of work sponsored by an agency of the
-- United States Government.  Neither the United States Government nor the United
-- States Department of Energy, nor Battelle, nor any of their employees, nor any
-- jurisdiction or organization that has cooperated in the development of these
-- materials, makes any warranty, express or implied, or assumes any legal
-- liability or responsibility for the accuracy, completeness, or usefulness or any
-- information, apparatus, product, software, or process disclosed, or represents
-- that its use would not infringe privately owned rights.
--
-- Reference herein to any specific commercial product, process, or service by
-- trade name, trademark, manufacturer, or otherwise does not necessarily
-- constitute or imply its endorsement, recommendation, or favoring by the United
-- States Government or any agency thereof, or Battelle Memorial Institute. The
-- views and opinions of authors expressed herein do not necessarily state or
-- reflect those of the United States Government or any agency thereof.
--
--                       PACIFIC NORTHWEST NATIONAL LABORATORY
--                                    operated by
--                                     BATTELLE
--                                      for the
--                        UNITED STATES DEPARTMENT OF ENERGY
--                         under Contract DE-AC05-76RL01830



-- Constructs a UBID code area using the given latitude and longitude coordinates and the given Open Location Code length.
--
-- @param _lat_lo [numeric] The south latitude coordinate.
-- @param _lng_lo [numeric] The west longitude coordinate.
-- @param _lat_hi [numeric] The north latitude coordinate.
-- @param _lng_hi [numeric] The east longitude coordinate.
-- @param _centroid_lat_lo [numeric] The south latitude coordinate for the centroid.
-- @param _centroid_lng_lo [numeric] The west longitude coordinate for the centroid.
-- @param _centroid_lat_hi [numeric] The north latitude coordinate for the centroid.
-- @param _centroid_lng_hi [numeric] The east longitude coordinate for the centroid.
-- @param _centroid_code_length [integer] The Open Location Code length for the centroid.
-- @return [Table<numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, integer>] The UBID code area.
-- @raise [invalid_parameter_value] If the given latitude and longitude coordinates are invalid, or if the given Open Location Code length is invalid.
CREATE OR REPLACE FUNCTION public.UBID_CodeArea(_lat_lo numeric, _lng_lo numeric, _lat_hi numeric, _lng_hi numeric, _centroid_lat_lo numeric, _centroid_lng_lo numeric, _centroid_lat_hi numeric, _centroid_lng_hi numeric, _centroid_code_length integer) RETURNS TABLE(lat_lo numeric, lng_lo numeric, lat_hi numeric, lng_hi numeric, centroid_lat_lo numeric, centroid_lng_lo numeric, centroid_lat_hi numeric, centroid_lng_hi numeric, centroid_code_length integer)
AS $$
DECLARE
  PAIR_CODE_LENGTH_ integer := 10;

  valid_lat boolean := UBID_ValidateLatitude(_lat_lo, _lat_hi, _centroid_lat_lo, _centroid_lat_hi);
  valid_lng boolean := UBID_ValidateLongitude(_lng_lo, _lng_hi, _centroid_lng_lo, _centroid_lng_hi);
BEGIN
  IF ((_centroid_code_length < 2) OR ((_centroid_code_length < PAIR_CODE_LENGTH_) AND (_centroid_code_length % 2 = 1))) THEN
      RAISE EXCEPTION 'Invalid Open Location Code length - %', _centroid_code_length
      USING ERRCODE = 'invalid_parameter_value', HINT = 'The Open Location Code length must be 2, 4, 6, 8, 10, 11, 12, 13, 14, or 15.';
  END IF;

  RETURN QUERY SELECT
    _lat_lo AS lat_lo,
    _lng_lo AS lng_lo,
    _lat_hi AS lat_hi,
    _lng_hi AS lng_hi,
    _centroid_lat_lo AS centroid_lat_lo,
    _centroid_lng_lo AS centroid_lng_lo,
    _centroid_lat_hi AS centroid_lat_hi,
    _centroid_lng_hi AS centroid_lng_hi,
    _centroid_code_length AS centroid_code_length;
END;
$$ LANGUAGE plpgsql;

-- Calculates the Jaccard index for the left and right UBID code areas.
--
-- The Jaccard index is a value between zero and one. The Jaccard index is the area of the intersection divided by the intersection of the union.
--
-- @param left_code_area [Table<numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, integer>] The left UBID code area.
-- @param right_code_area [Table<numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, integer>] The right UBID code area.
-- @return [numeric] The Jaccard index.
CREATE OR REPLACE FUNCTION public.UBID_CodeArea_Jaccard(left_code_area record, right_code_area record) RETURNS numeric
AS $$
DECLARE
  intersection_lat_lo numeric := GREATEST(left_code_area.lat_lo, right_code_area.lat_lo);
  intersection_lat_hi numeric := LEAST(left_code_area.lat_hi, right_code_area.lat_hi);
  intersection_lng_lo numeric := GREATEST(left_code_area.lng_lo, right_code_area.lng_lo);
  intersection_lng_hi numeric := LEAST(left_code_area.lng_hi, right_code_area.lng_hi);

  intersection_area numeric;

  left_area numeric;
  right_area numeric;
BEGIN
  IF ((intersection_lat_lo > intersection_lat_hi) OR (intersection_lng_lo > intersection_lng_hi)) THEN
    RETURN 0;
  END IF;

  intersection_area := (intersection_lat_hi - intersection_lat_lo) * (intersection_lng_hi - intersection_lng_lo);

  left_area := (left_code_area.lat_hi - left_code_area.lat_lo) * (left_code_area.lng_hi - left_code_area.lng_lo);
  right_area := (right_code_area.lat_hi - right_code_area.lat_lo) * (right_code_area.lng_hi - right_code_area.lng_lo);

  RETURN intersection_area / (left_area + right_area - intersection_area);
END;
$$ LANGUAGE plpgsql;

-- Decodes the given UBID code.
--
-- @param code [text] The UBID code.
-- @return [Table<numeric, numeric, numeric, numeric, numeric, numeric, numeric, numeric, integer>] The UBID code area for the given UBID code.
-- @raise [invalid_parameter_value] If the given UBID code is invalid.
CREATE OR REPLACE FUNCTION public.UBID_Decode(code text) RETURNS record
AS $$
DECLARE
  result record := UBID_Parse(code);

  lat_measure numeric := result.centroid_lat_hi - result.centroid_lat_lo;
  lng_measure numeric := result.centroid_lng_hi - result.centroid_lng_lo;

  lat_lo numeric := result.centroid_lat_lo - (result.south * lat_measure);
  lng_lo numeric := result.centroid_lng_lo - (result.west * lng_measure);
  lat_hi numeric := result.centroid_lat_hi + (result.north * lat_measure);
  lng_hi numeric := result.centroid_lng_hi + (result.east * lng_measure);
BEGIN
  RETURN UBID_CodeArea(lat_lo, lng_lo, lat_hi, lng_hi, result.centroid_lat_lo, result.centroid_lng_lo, result.centroid_lat_hi, result.centroid_lng_hi, result.centroid_code_length);
END;
$$ LANGUAGE plpgsql;

-- Encodes the given latitude and longitude coordinates as a UBID code with the given Open Location Code length.
--
-- @param lat_lo [numeric] The south latitude coordinate.
-- @param lng_lo [numeric] The west longitude coordinate.
-- @param lat_hi [numeric] The north latitude coordinate.
-- @param lng_hi [numeric] The east longitude coordinate.
-- @param centroid_lat [numeric] The south latitude coordinate for the centroid.
-- @param centroid_lng [numeric] The west longitude coordinate for the centroid.
-- @param code_length [integer] The Open Location Code length (default: 10).
-- @return [text] The UBID code.
-- @raise [invalid_parameter_value] If the given latitude and longitude coordinates are invalid, or if the given Open Location Code length is invalid.
CREATE OR REPLACE FUNCTION public.UBID_Encode(lat_lo numeric, lng_lo numeric, lat_hi numeric, lng_hi numeric, centroid_lat numeric, centroid_lng numeric, code_length integer DEFAULT 10) RETURNS text
AS $$
DECLARE
  SEPARATOR_ text := '-';

  valid_lat boolean := UBID_ValidateLatitude(lat_lo, lat_hi, centroid_lat, centroid_lat);
  valid_lng boolean := UBID_ValidateLongitude(lng_lo, lng_hi, centroid_lng, centroid_lng);

  code_lo text := pluscode_encode(lat_lo, lng_lo, code_length);
  code_hi text := pluscode_encode(lat_hi, lng_hi, code_length);
  code_centroid text := pluscode_encode(centroid_lat, centroid_lng, code_length);

  code_area_lo record := pluscode_decode(code_lo);
  code_area_hi record := pluscode_decode(code_hi);
  code_area_centroid record := pluscode_decode(code_centroid);

  lat_measure numeric := code_area_centroid.lat_hi - code_area_centroid.lat_lo;
  lng_measure numeric := code_area_centroid.lng_hi - code_area_centroid.lng_lo;

  north integer := round((code_area_hi.lat_hi - code_area_centroid.lat_hi) / lat_measure);
  east integer := round((code_area_hi.lng_hi - code_area_centroid.lng_hi) / lng_measure);
  south integer := round((code_area_centroid.lat_lo - code_area_lo.lat_lo) / lat_measure);
  west integer := round((code_area_centroid.lng_lo - code_area_lo.lng_lo) / lng_measure);

  code text := code_centroid || SEPARATOR_ || north || SEPARATOR_ || east || SEPARATOR_ || south || SEPARATOR_ || west;
BEGIN
  RETURN code;
END;
$$ LANGUAGE plpgsql;

-- Encodes the given latitude and longitude coordinates for the centroid only as a UBID code with the given Open Location Code length.
--
-- Note: The north, east, south and west extents for UBID codes that are returned by this function are always equal to zero.
--
-- @param centroid_lat [numeric] The south latitude coordinate for the centroid.
-- @param centroid_lng [numeric] The west longitude coordinate for the centroid.
-- @param code_length [integer] The Open Location Code length (default: 10).
-- @return [text] The UBID code.
-- @raise [invalid_parameter_value] If the given latitude and longitude coordinates are invalid, or if the given Open Location Code length is invalid.
CREATE OR REPLACE FUNCTION public.UBID_EncodeCentroid(centroid_lat numeric, centroid_lng numeric, code_length integer DEFAULT 10) RETURNS text
AS $$
DECLARE
  lat_lo numeric := centroid_lat;
  lng_lo numeric := centroid_lng;
  lat_hi numeric := centroid_lat;
  lng_hi numeric := centroid_lng;
BEGIN
  RETURN UBID_Encode(lat_lo, lng_lo, lat_hi, lng_hi, centroid_lat, centroid_lng, code_length);
END;
$$ LANGUAGE plpgsql;

-- Parse the given UBID code.
--
-- @param code [text] The UBID code.
-- @return [Table<numeric, numeric, numeric, numeric, integer, integer, integer, integer, integer>] The latitude and longitude coordinates for the centroid, the Open Location code length, and the north, east, south and west extents.
-- @raise [invalid_parameter_value] If the given UBID code is invalid.
CREATE OR REPLACE FUNCTION public.UBID_Parse(code text) RETURNS TABLE(centroid_lat_lo numeric, centroid_lng_lo numeric, centroid_lat_hi numeric, centroid_lng_hi numeric, centroid_code_length integer, north integer, east integer, south integer, west integer)
AS $$
DECLARE
  SEPARATOR_ text := '-';
  NON_NEGATIVE_INTEGER_PATTERN_ text := '^(?:0|[1-9][0-9]*)$';

  parts text[] := regexp_split_to_array(code, SEPARATOR_);

  centroid_code_area record;
BEGIN
  IF (array_length(parts, 1) != 5) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The code must have exactly five parts, separated by hyphen "-" characters.';
  ELSIF (pluscode_isFull(parts[1]) IS FALSE) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The first part of the code must be a full Open Location Code.';
  ELSIF (parts[2] !~ NON_NEGATIVE_INTEGER_PATTERN_) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The second part of the code must be a non-negative integer.';
  ELSIF (parts[3] !~ NON_NEGATIVE_INTEGER_PATTERN_) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The third part of the code must be a non-negative integer.';
  ELSIF (parts[4] !~ NON_NEGATIVE_INTEGER_PATTERN_) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The fourth part of the code must be a non-negative integer.';
  ELSIF (parts[5] !~ NON_NEGATIVE_INTEGER_PATTERN_) THEN
    RAISE EXCEPTION 'Passed UBID is not a valid code - %', code
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The fifth part of the code must be a non-negative integer.';
  ELSE
    centroid_code_area := pluscode_decode(parts[1]);

    RETURN QUERY SELECT
      centroid_code_area.lat_lo AS centroid_lat_lo,
      centroid_code_area.lng_lo AS centroid_lng_lo,
      centroid_code_area.lat_hi AS centroid_lat_hi,
      centroid_code_area.lng_hi AS centroid_lng_hi,
      centroid_code_area.code_length::integer AS centroid_code_length,
      to_number(parts[2], repeat('9', char_length(parts[2])))::integer AS north,
      to_number(parts[3], repeat('9', char_length(parts[3])))::integer AS east,
      to_number(parts[4], repeat('9', char_length(parts[4])))::integer AS south,
      to_number(parts[5], repeat('9', char_length(parts[5])))::integer AS west;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Is the given UBID code valid?
--
-- @param code [text] The UBID code.
-- @return [boolean] TRUE if the given UBID code is valid. Otherwise, FALSE.
CREATE OR REPLACE FUNCTION public.UBID_IsValid(code text) RETURNS boolean
AS $$
DECLARE
  SEPARATOR_ text := '-';
  NON_NEGATIVE_INTEGER_PATTERN_ text := '^(?:0|[1-9][0-9]*)$';

  parts text[] := regexp_split_to_array(code, SEPARATOR_);
BEGIN
  RETURN (array_length(parts, 1) = 5)
    AND (pluscode_isFull(parts[1]) IS TRUE)
    AND (parts[2] ~ NON_NEGATIVE_INTEGER_PATTERN_)
    AND (parts[3] ~ NON_NEGATIVE_INTEGER_PATTERN_)
    AND (parts[4] ~ NON_NEGATIVE_INTEGER_PATTERN_)
    AND (parts[5] ~ NON_NEGATIVE_INTEGER_PATTERN_);
END;
$$ LANGUAGE plpgsql;

-- Validates that the following chain of inequalities holds for the given latitude coordinates:
--
--   -90 <= lat_lo <= centroid_lat_lo <= centroid_lat_hi <= lat_hi <= 90
--
-- @param lat_lo [numeric] The least latitude coordinate.
-- @param lat_hi [numeric] The greatest latitude coordinate.
-- @param centroid_lat_lo [numeric] The least latitude coordinate for the centroid.
-- @param centroid_lat_hi [numeric] The greatest latitude coordinate for the centroid.
-- @return [boolean] TRUE if the chain of inequalities holds. Otherwise, FALSE.
-- @raise [invalid_parameter_value] If the given latitude coordinates are invalid.
CREATE OR REPLACE FUNCTION public.UBID_ValidateLatitude(lat_lo numeric, lat_hi numeric, centroid_lat_lo numeric, centroid_lat_hi numeric) RETURNS boolean
AS $$
DECLARE
  LATITUDE_MAX_ integer := 90;
BEGIN
  IF (lat_hi > LATITUDE_MAX_) THEN
    RAISE EXCEPTION 'Invalid maximum latitude coordinate - %', lat_hi
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The maximum latitude coordinate must be less than or equal to ' || LATITUDE_MAX_ || '.';
  ELSIF (centroid_lat_hi > lat_hi) THEN
    RAISE EXCEPTION 'Invalid centroid maximum latitude coordinate - %', centroid_lat_hi
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The centroid latitude coordinate cannot be greater than the maximum latitude coordinate.';
  ELSIF (lat_lo > centroid_lat_lo) THEN
    RAISE EXCEPTION 'Invalid centroid minimum latitude coordinate - %', centroid_lat_lo
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The minimum latitude coordinate cannot be greater than the centroid latitude coordinate.';
  ELSIF (lat_lo < (-LATITUDE_MAX_)) THEN
    RAISE EXCEPTION 'Invalid minimum latitude coordinate - %', lat_lo
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The minimum latitude coordinate must be greater than or equal to ' || (-LATITUDE_MAX_) || '.';
  ELSE
    RETURN TRUE;
  END IF;
END;
$$ LANGUAGE plpgsql;

-- Validates that the following chain of inequalities holds for the given longitude coordinates:
--
--   -180 <= lng_lo <= centroid_lng_lo <= centroid_lng_hi <= lng_hi <= 180
--
-- @param lng_lo [numeric] The least longitude coordinate.
-- @param lng_hi [numeric] The greatest longitude coordinate.
-- @param centroid_lng_lo [numeric] The least longitude coordinate for the centroid.
-- @param centroid_lng_hi [numeric] The greatest longitude coordinate for the centroid.
-- @return [boolean] TRUE if the chain of inequalities holds. Otherwise, FALSE.
-- @raise [invalid_parameter_value] If the given longitude coordinates are invalid.
CREATE OR REPLACE FUNCTION public.UBID_ValidateLongitude(lng_lo numeric, lng_hi numeric, centroid_lng_lo numeric, centroid_lng_hi numeric) RETURNS boolean
AS $$
DECLARE
  LONGITUDE_MAX_ integer := 180;
BEGIN
  IF (lng_hi > LONGITUDE_MAX_) THEN
    RAISE EXCEPTION 'Invalid maximum longitude coordinate - %', lng_hi
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The maximum longitude coordinate must be less than or equal to ' || LONGITUDE_MAX_ || '.';
  ELSIF (centroid_lng_hi > lng_hi) THEN
    RAISE EXCEPTION 'Invalid centroid maximum longitude coordinate - %', centroid_lng_hi
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The centroid longitude coordinate cannot be greater than the maximum longitude coordinate.';
  ELSIF (lng_lo > centroid_lng_lo) THEN
    RAISE EXCEPTION 'Invalid centroid minimum longitude coordinate - %', centroid_lng_lo
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The minimum longitude coordinate cannot be greater than the centroid longitude coordinate.';
  ELSIF (lng_lo < (-LONGITUDE_MAX_)) THEN
    RAISE EXCEPTION 'Invalid minimum longitude coordinate - %', lng_lo
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The minimum longitude coordinate must be greater than or equal to ' || (-LONGITUDE_MAX_) || '.';
  ELSE
    RETURN TRUE;
  END IF;
END;
$$ LANGUAGE plpgsql;
