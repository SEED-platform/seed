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


-- Decodes the given UBID code.
--
-- @param code [text] The UBID code.
-- @return [Table<geometry, geometry, integer>] The envelopes for the axis-aligned minimum bounding box and centroid, and the Open Location Code length for the centroid.
-- @raise [invalid_parameter_value] If the given UBID code is invalid.
CREATE OR REPLACE FUNCTION public.UBID_DecodeGeom(code text) RETURNS TABLE(bbox geometry, centroid geometry, centroid_code_length integer)
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
  RETURN QUERY SELECT
    ST_MakeEnvelope(lng_lo, lat_lo, lng_hi, lat_hi, 4326) AS bbox,
    ST_MakeEnvelope(result.centroid_lng_lo, result.centroid_lat_lo, result.centroid_lng_hi, result.centroid_lat_hi, 4326) AS centroid,
    result.centroid_code_length AS centroid_code_length;
END;
$$ LANGUAGE plpgsql;

-- Encodes the given geometry as a UBID code with the given Open Location Code length.
--
-- @param the_geom [geometry] The geometry.
-- @param code_length [integer] The Open Location Code length (default: 10).
-- @return [text] The UBID code.
-- @raise [invalid_parameter_value] If the given geometry is invalid or if the given Open Location Code length is invalid.
CREATE OR REPLACE FUNCTION public.UBID_EncodeGeom(the_geom geometry, code_length integer DEFAULT 10) RETURNS text
AS $$
DECLARE
  lat_lo numeric;
  lng_lo numeric;
  lat_hi numeric;
  lng_hi numeric;

  centroid geometry;
  centroid_lat numeric;
  centroid_lng numeric;
BEGIN
  IF (ST_SRID(the_geom) != 4326) THEN
    RAISE EXCEPTION 'Invalid SRID for geometry - %', ST_SRID(the_geom)
    USING ERRCODE = 'invalid_parameter_value', HINT = 'The SRID for the geometry must be equal to 4326.';
  END IF;

  lat_lo := ST_YMin(the_geom);
  lng_lo := ST_XMin(the_geom);
  lat_hi := ST_YMax(the_geom);
  lng_hi := ST_XMax(the_geom);

  centroid := ST_Centroid(the_geom);
  centroid_lat := ST_Y(centroid);
  centroid_lng := ST_X(centroid);

  RETURN UBID_Encode(lat_lo, lng_lo, lat_hi, lng_hi, centroid_lat, centroid_lng, code_length);
END;
$$ LANGUAGE plpgsql;
