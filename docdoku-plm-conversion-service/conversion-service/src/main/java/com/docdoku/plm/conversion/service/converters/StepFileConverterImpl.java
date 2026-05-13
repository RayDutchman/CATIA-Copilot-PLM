
package com.docdoku.plm.conversion.service.converters;


import com.docdoku.plm.server.converters.CADConverter;
import com.docdoku.plm.server.converters.ConversionResultProxy;
import com.docdoku.plm.server.converters.ConverterUtils;

import javax.enterprise.context.ApplicationScoped;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Properties;
import java.util.UUID;
import java.util.logging.Level;
import java.util.logging.Logger;

@ApplicationScoped
public class StepFileConverterImpl implements CADConverter {

    private static final Logger LOGGER = Logger.getLogger(StepFileConverterImpl.class.getName());
    private static final String CONF_PROPERTIES = "/com/docdoku/plm/conversion/service/converters/step/conf.properties";
    private static final String PYTHON_SCRIPT_TO_OBJ = "/com/docdoku/plm/conversion/service/converters/step/convert_step_obj.py";
    private static final Properties CONF = new Properties();

    static {
        try (InputStream inputStream = StepFileConverterImpl.class.getResourceAsStream(CONF_PROPERTIES)) {
            CONF.load(inputStream);
        } catch (IOException e) {
            LOGGER.log(Level.SEVERE, null, e);
        }
    }

    @Override
    public ConversionResultProxy convert(final URI cadFileUri, final URI tmpDirUri)
            throws ConversionException {
        String pythonInterpreter = CONF.getProperty("pythonInterpreter");
        String freeCadLibPath = CONF.getProperty("freeCadLibPath");

        Path tmpDir = Paths.get(tmpDirUri);
        Path tmpCadFile = Paths.get(cadFileUri);

        UUID uuid = UUID.randomUUID();
        Path tmpOBJFile = tmpDir.resolve(uuid + ".obj");

        Path scriptToOBJ = tmpDir.resolve("python_script" + uuid + ".py");
        try (InputStream scriptStream = StepFileConverterImpl.class.getResourceAsStream(PYTHON_SCRIPT_TO_OBJ)) {
            Files.copy(scriptStream, scriptToOBJ);
        } catch (IOException | NullPointerException e) {
            throw new ConversionException("Unable to copy python script", e);
        }

        String[] args = {pythonInterpreter, scriptToOBJ.toAbsolutePath().toString(), "-l", freeCadLibPath, "-i",
                tmpCadFile.toAbsolutePath().toString(), "-o", tmpOBJFile.toAbsolutePath().toString()};
        ProcessBuilder pb = new ProcessBuilder(args);

        try {
            Process process = pb.start();

            // Read buffers
            String stdOutput = ConverterUtils.inputStreamToString(process.getInputStream());
            String errorOutput = ConverterUtils.inputStreamToString(process.getErrorStream());

            LOGGER.info(stdOutput);

            process.waitFor();

            if (process.exitValue() == 0) {
                return new ConversionResultProxy(tmpOBJFile);
            } else {
                throw new ConversionException(
                        "Cannot convert to obj " + tmpCadFile.toAbsolutePath() + ": " + errorOutput);
            }
        } catch (IOException | InterruptedException e) {
            LOGGER.log(Level.SEVERE, null, e);
            throw new ConversionException(e);
        }
    }

    @Override
    public boolean canConvertToOBJ(String cadFileExtension) {
        return Arrays.asList("stp", "step", "igs", "iges").contains(cadFileExtension);
    }

}
