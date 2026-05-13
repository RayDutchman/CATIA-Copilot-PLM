package com.docdoku.plm.conversion.service;

import javax.inject.Singleton;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Path;
import java.util.logging.Level;
import java.util.logging.Logger;

@Singleton
public class GeometryParser {

        private static final Logger LOGGER = Logger.getLogger(GeometryParser.class.getName());

        public GeometryParser() {
        }

        /**
         * Computes the bounding box of given 3D OBJ file
         *
         * @param path path to resource
         * @return an array of double representing the bounding box min and max values
         */
        public double[] calculateBox(Path path) {

            boolean init = false;
            Double xMin = 0.0, xMax = 0.0, yMin = 0.0, yMax = 0.0, zMin = 0.0, zMax = 0.0;

            try (BufferedReader br = new BufferedReader(new FileReader(path.toFile()))) {
                String line;
                while ((line = br.readLine()) != null) {

                    if(line.startsWith("v  ")){
                        String[] v = line.replace("v  ", "").split(" ");
                        double x = Double.valueOf(v[0]);
                        double y = Double.valueOf(v[1]);
                        double z = Double.valueOf(v[2]);
                        if(!init){
                            xMin = x ;
                            xMax = x ;
                            yMin = y ;
                            yMax = y ;
                            zMin = z ;
                            zMax = z ;
                            init = true;
                        } else{
                            xMin = Math.min(x, xMin);
                            xMax = Math.max(x, xMax);
                            yMin = Math.min(y, yMin);
                            yMax = Math.max(y, yMax);
                            zMin = Math.min(z, zMin);
                            zMax = Math.max(z, zMax);
                        }

                    }
                }
            } catch (IOException e) {
                LOGGER.log(Level.SEVERE, "Cannot parse vertices from obj", e);
            } catch (NumberFormatException e) {
                LOGGER.log(Level.SEVERE, "Cannot parse double value", e);
            }


            double[] result = new double[6];

            result[0] = xMin;
            result[1] = yMin;
            result[2] = zMin;
            result[3] = xMax;
            result[4] = yMax;
            result[5] = zMax;
            return result;
        }


}
