package com.docdoku.plm.conversion.service;

import javax.inject.Singleton;
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.util.logging.Level;
import java.util.logging.Logger;

@Singleton
public class GeometryParser {

    private static final Logger LOGGER = Logger.getLogger(GeometryParser.class.getName());

    public GeometryParser() {
    }

    /**
     * Computes the bounding box of a 3D geometry file.
     * Supports OBJ (text) and GLB (binary glTF 2.0).
     *
     * @param path path to resource
     * @return double[6]: {xMin, yMin, zMin, xMax, yMax, zMax}
     */
    public double[] calculateBox(Path path) {
        String fileName = path.getFileName().toString().toLowerCase();
        if (fileName.endsWith(".glb")) {
            return calculateBoxFromGlb(path);
        } else {
            return calculateBoxFromObj(path);
        }
    }

    /**
     * Parse bounding box from OBJ text file by scanning vertex lines.
     */
    private double[] calculateBoxFromObj(Path path) {
        boolean init = false;
        double xMin = 0, xMax = 0, yMin = 0, yMax = 0, zMin = 0, zMax = 0;

        try (BufferedReader br = new BufferedReader(new FileReader(path.toFile()))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (line.startsWith("v ") || line.startsWith("v  ")) {
                    // Handle both "v x y z" and "v  x y z" formats
                    String trimmed = line.substring(1).trim();
                    String[] parts = trimmed.split("\\s+");
                    if (parts.length >= 3) {
                        double x = Double.parseDouble(parts[0]);
                        double y = Double.parseDouble(parts[1]);
                        double z = Double.parseDouble(parts[2]);
                        if (!init) {
                            xMin = xMax = x;
                            yMin = yMax = y;
                            zMin = zMax = z;
                            init = true;
                        } else {
                            xMin = Math.min(x, xMin); xMax = Math.max(x, xMax);
                            yMin = Math.min(y, yMin); yMax = Math.max(y, yMax);
                            zMin = Math.min(z, zMin); zMax = Math.max(z, zMax);
                        }
                    }
                }
            }
        } catch (IOException e) {
            LOGGER.log(Level.SEVERE, "Cannot parse vertices from obj", e);
        } catch (NumberFormatException e) {
            LOGGER.log(Level.SEVERE, "Cannot parse double value from obj", e);
        }

        return new double[]{xMin, yMin, zMin, xMax, yMax, zMax};
    }

    /**
     * Parse bounding box from GLB (binary glTF 2.0) file.
     *
     * GLB layout:
     *   12 bytes header  (magic 0x46546C67, version, totalLength)
     *   Chunk 0: JSON  (chunkLength, chunkType 0x4E4F534A, chunkData)
     *   Chunk 1: BIN   (chunkLength, chunkType 0x004E4942, chunkData)
     *
     * The JSON chunk contains the glTF asset definition.
     * Each POSITION accessor has "min" and "max" arrays [x, y, z].
     * We aggregate across all accessors to get the global bounding box.
     */
    private double[] calculateBoxFromGlb(Path path) {
        double xMin = 0, xMax = 0, yMin = 0, yMax = 0, zMin = 0, zMax = 0;
        boolean init = false;

        try (RandomAccessFile raf = new RandomAccessFile(path.toFile(), "r")) {

            // Read GLB header
            byte[] header = new byte[12];
            raf.readFully(header);
            ByteBuffer hdr = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN);
            int magic = hdr.getInt();
            // 0x46546C67 = "glTF"
            if (magic != 0x46546C67) {
                LOGGER.warning("Not a valid GLB file: " + path);
                return new double[]{0, 0, 0, 0, 0, 0};
            }
            // int version = hdr.getInt(); // skip
            // int totalLen = hdr.getInt(); // skip

            // Read chunk 0 (JSON)
            byte[] chunkHeader = new byte[8];
            raf.readFully(chunkHeader);
            ByteBuffer ch = ByteBuffer.wrap(chunkHeader).order(ByteOrder.LITTLE_ENDIAN);
            int chunkLength = ch.getInt();
            int chunkType   = ch.getInt();

            // chunkType 0x4E4F534A = "JSON"
            if (chunkType != 0x4E4F534A) {
                LOGGER.warning("First GLB chunk is not JSON: " + path);
                return new double[]{0, 0, 0, 0, 0, 0};
            }

            byte[] jsonBytes = new byte[chunkLength];
            raf.readFully(jsonBytes);
            String json = new String(jsonBytes, StandardCharsets.UTF_8);

            // Extract min/max from all POSITION accessors
            // Pattern: "min":[x,y,z],"max":[x,y,z] near "POSITION"
            // We parse all "min" and "max" arrays from accessor objects.
            // Simple approach: find all occurrences of "min":[ and "max":[ in the JSON.
            double[] globalMin = extractMinMaxFromGltfJson(json, "min");
            double[] globalMax = extractMinMaxFromGltfJson(json, "max");

            if (globalMin != null && globalMax != null) {
                xMin = globalMin[0]; yMin = globalMin[1]; zMin = globalMin[2];
                xMax = globalMax[0]; yMax = globalMax[1]; zMax = globalMax[2];
                init = true;
            }

        } catch (IOException e) {
            LOGGER.log(Level.SEVERE, "Cannot parse GLB bounding box from: " + path, e);
        }

        if (!init) {
            LOGGER.warning("Could not extract bounding box from GLB: " + path + " — using zeros");
        }

        return new double[]{xMin, yMin, zMin, xMax, yMax, zMax};
    }

    /**
     * Extract the global min or max vec3 values from a glTF JSON string
     * by finding all "min":[...] or "max":[...] entries in accessor objects
     * and computing the overall min/max across all of them.
     *
     * @param json     glTF JSON content
     * @param key      "min" or "max"
     * @return double[3] global {x, y, z}, or null if not found
     */
    private double[] extractMinMaxFromGltfJson(String json, String key) {
        String searchKey = "\"" + key + "\":[";
        boolean isMin = key.equals("min");

        double rx = isMin ? Double.MAX_VALUE : -Double.MAX_VALUE;
        double ry = isMin ? Double.MAX_VALUE : -Double.MAX_VALUE;
        double rz = isMin ? Double.MAX_VALUE : -Double.MAX_VALUE;
        boolean found = false;

        int idx = 0;
        while ((idx = json.indexOf(searchKey, idx)) != -1) {
            int start = idx + searchKey.length();
            int end   = json.indexOf(']', start);
            if (end < 0) break;
            String arrayStr = json.substring(start, end);
            String[] parts = arrayStr.split(",");
            if (parts.length >= 3) {
                try {
                    double x = Double.parseDouble(parts[0].trim());
                    double y = Double.parseDouble(parts[1].trim());
                    double z = Double.parseDouble(parts[2].trim());
                    if (isMin) {
                        rx = Math.min(rx, x);
                        ry = Math.min(ry, y);
                        rz = Math.min(rz, z);
                    } else {
                        rx = Math.max(rx, x);
                        ry = Math.max(ry, y);
                        rz = Math.max(rz, z);
                    }
                    found = true;
                } catch (NumberFormatException e) {
                    // skip malformed entry
                }
            }
            idx = end;
        }

        return found ? new double[]{rx, ry, rz} : null;
    }

}
