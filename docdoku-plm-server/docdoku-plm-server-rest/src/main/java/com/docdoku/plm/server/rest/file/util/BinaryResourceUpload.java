/*
 * DocDoku, Professional Open Source
 * Copyright 2006 - 2020 DocDoku SARL
 *
 * This file is part of DocDokuPLM.
 *
 * DocDokuPLM is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * DocDokuPLM is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with DocDokuPLM.  If not, see <http://www.gnu.org/licenses/>.
 */

package com.docdoku.plm.server.rest.file.util;


import com.docdoku.plm.server.core.util.FileIO;

import javax.servlet.http.Part;
import javax.ws.rs.core.MediaType;
import javax.ws.rs.core.Response;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * @author Taylor LABEJOF
 */
public class BinaryResourceUpload {
    private static final Logger LOGGER = Logger.getLogger(BinaryResourceUpload.class.getName());

    private BinaryResourceUpload() {
        super();
    }


    /**
     * Upload a form file in a specific output
     *
     * @param outputStream BinaryResource output stream (in server vault repository)
     * @param formPart     The form part list
     * @return The length of the file uploaded
     */
    public static long uploadBinary(OutputStream outputStream, Part formPart)
            throws IOException {
        long length;
        try (InputStream in = formPart.getInputStream(); OutputStream out = outputStream) {
            length =  FileIO.copy(in, out);
        }
        return length;
    }

    /**
     * Log error & return a 500 error.
     *
     * @param e The exception which cause the error.
     * @return A 500 error.
     */
    public static Response uploadError(Exception e) {
        String message = "Error while uploading the file(s).";
        LOGGER.log(Level.SEVERE, message, e);
        return Response.status(Response.Status.INTERNAL_SERVER_ERROR)
                .header("Reason-Phrase", message)
                .entity(message)
                .type(MediaType.TEXT_PLAIN)
                .build();
    }

    public static Response tryToRespondCreated(String uri) {
        try {
            // 使用 URI(String) 构造时，空格等特殊字符会导致 URISyntaxException。
            // 先将 URLEncoder 编出的 '+' 替换为 '%20'，确保空格被正确编码为合法 URI 字符。
            String safeUri = uri.replace("+", "%20");
            return Response.created(new URI(safeUri)).build();
        } catch (URISyntaxException e) {
            LOGGER.log(Level.WARNING, "Failed to build created URI: " + uri, e);
            return Response.ok().build();
        }
    }
}
