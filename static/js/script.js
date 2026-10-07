// ==========================================
// NAVIGATION
// ==========================================

function showSection(sectionId) {

    const sections = document.querySelectorAll(".section");
    const buttons = document.querySelectorAll(".nav-btn");

    sections.forEach(function(section) {
        section.classList.remove("active-section");
    });

    buttons.forEach(function(button) {
        button.classList.remove("active");
    });

    const selectedSection = document.getElementById(sectionId);

    if (selectedSection) {
        selectedSection.classList.add("active-section");
    }

    buttons.forEach(function(button) {

        const buttonText = button.textContent
            .trim()
            .toLowerCase();

        if (
            (sectionId === "home" && buttonText === "home") ||
            (sectionId === "detect" && buttonText === "detect ppe") ||
            (sectionId === "results" && buttonText === "results") ||
            (sectionId === "guide" && buttonText === "safety guide") ||
            (sectionId === "about" && buttonText === "about")
        ) {
            button.classList.add("active");
        }
    });

    window.scrollTo({
        top: 0,
        behavior: "smooth"
    });
}


// ==========================================
// FILE NAME DISPLAY
// ==========================================

function showFileName(input, outputId) {

    const output = document.getElementById(outputId);

    if (!output) {
        return;
    }

    if (input.files && input.files.length > 0) {

        output.textContent =
            "Selected: " + input.files[0].name;

    } else {

        output.textContent =
            "No file selected";
    }
}


// ==========================================
// IMAGE DETECTION
// ==========================================

function setupImageDetection() {

    const form = document.getElementById("imageForm");

    if (!form) {
        return;
    }

    form.addEventListener("submit", async function(event) {

        event.preventDefault();

        const fileInput =
            form.querySelector('input[type="file"]');

        const resultContent =
            document.getElementById("resultContent");

        if (!fileInput || !fileInput.files.length) {

            alert("Please select an image first.");
            return;
        }

        const formData = new FormData();

        formData.append(
            "image",
            fileInput.files[0]
        );

        resultContent.innerHTML = `
            <div class="empty-result">
                <div class="result-icon">⏳</div>
                <h3>Detecting PPE...</h3>
                <p>
                    Please wait while the YOLO model
                    analyzes the image.
                </p>
            </div>
        `;

        showSection("results");

        try {

            const response = await fetch(
                "/detect/image",
                {
                    method: "POST",
                    body: formData
                }
            );

            const data = await response.json();

            if (!response.ok || !data.success) {

                throw new Error(
                    data.message ||
                    "Image detection failed."
                );
            }


            // ======================================
            // RESULT IMAGE
            // ======================================

            const imageContainer =
                document.createElement("div");

            imageContainer.className =
                "result-media";

            const resultImage =
                document.createElement("img");

            resultImage.src =
                data.result_url;

            resultImage.alt =
                "PPE Detection Result";

            resultImage.className =
                "result-image";

            imageContainer.appendChild(
                resultImage
            );


            // ======================================
            // IMAGE SUMMARY
            // ======================================

            const summary =
                document.createElement("div");

            summary.className =
                "detection-summary";

            summary.innerHTML = `
                <h3>Image Detection Summary</h3>

                <p class="detection-status">
                    ✓ PPE detection completed successfully.
                </p>
            `;


            // ======================================
            // GET SUMMARY FROM BACKEND
            // ======================================

            const ppeSummary =
                data.summary || {};


            // ======================================
            // SUMMARY TABLE
            // ======================================

            const table =
                document.createElement("table");

            table.className =
                "ppe-summary-table";

            table.innerHTML = `
                <thead>
                    <tr>
                        <th>PPE / Object</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>

                    <tr>
                        <td>👷 Person</td>
                        <td>${ppeSummary.person || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>🪖 Hard Hat</td>
                        <td>${ppeSummary.hard_hat || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>😷 Mask</td>
                        <td>${ppeSummary.mask || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>🦺 Safety Vest</td>
                        <td>${ppeSummary.safety_vest || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>⚠️ No Hard Hat</td>
                        <td>${ppeSummary.no_hard_hat || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>⚠️ No Mask</td>
                        <td>${ppeSummary.no_mask || "Not Detected"}</td>
                    </tr>

                    <tr>
                        <td>⚠️ No Safety Vest</td>
                        <td>${ppeSummary.no_safety_vest || "Not Detected"}</td>
                    </tr>

                </tbody>
            `;

            summary.appendChild(table);


            // ======================================
            // FALLBACK FOR OLDER RESPONSE
            // ======================================

            if (!data.summary) {

                const detectedList =
                    document.createElement("div");

                detectedList.innerHTML = `
                    <h4>Detected Objects</h4>
                `;

                if (
                    data.detected_objects &&
                    data.detected_objects.length > 0
                ) {

                    data.detected_objects.forEach(
                        function(objectName) {

                            const item =
                                document.createElement("p");

                            item.textContent =
                                "✓ " +
                                objectName +
                                " — Detected";

                            detectedList.appendChild(item);
                        }
                    );

                } else {

                    detectedList.innerHTML += `
                        <p>No objects detected.</p>
                    `;
                }

                summary.appendChild(
                    detectedList
                );
            }


            // ======================================
            // DISPLAY IMAGE RESULT
            // ======================================

            resultContent.innerHTML = "";

            resultContent.appendChild(
                imageContainer
            );

            resultContent.appendChild(
                summary
            );

        } catch (error) {

            resultContent.innerHTML = `
                <div class="empty-result">

                    <div class="result-icon">❌</div>

                    <h3>Detection Failed</h3>

                    <p>
                        ${error.message}
                    </p>

                </div>
            `;
        }

    });
}


// ==========================================
// VIDEO DETECTION
// ==========================================

function setupVideoDetection() {

    const form =
        document.getElementById("videoForm");

    if (!form) {
        return;
    }

    form.addEventListener(
        "submit",
        async function(event) {

            event.preventDefault();

            const fileInput =
                form.querySelector(
                    'input[type="file"]'
                );

            const resultContent =
                document.getElementById(
                    "resultContent"
                );

            if (
                !fileInput ||
                !fileInput.files.length
            ) {

                alert(
                    "Please select a video first."
                );

                return;
            }

            const formData =
                new FormData();

            formData.append(
                "video",
                fileInput.files[0]
            );

            resultContent.innerHTML = `
                <div class="empty-result">

                    <div class="result-icon">
                        ⏳
                    </div>

                    <h3>
                        Processing Video...
                    </h3>

                    <p>
                        Please wait while the YOLO
                        model analyzes the video.
                    </p>

                </div>
            `;

            showSection("results");

            try {

                const response =
                    await fetch(
                        "/detect/video",
                        {
                            method: "POST",
                            body: formData
                        }
                    );

                const data =
                    await response.json();

                if (
                    !response.ok ||
                    !data.success
                ) {

                    throw new Error(
                        data.message ||
                        "Video detection failed."
                    );
                }


                // ==================================
                // GET PERSON SUMMARIES
                // ==================================

                const persons =
                    Array.isArray(
                        data.person_summaries
                    )
                    ? data.person_summaries
                    : [];


                // ==================================
                // BUILD PERSON SUMMARY
                // ==================================

                let personSummaryHTML = "";


                if (persons.length > 0) {

                    personSummaryHTML = `

                        <div
                            class="person-detection-summary"
                        >

                            <h3>
                                👷 Person-wise PPE Detection
                            </h3>

                            <p>
                                The video contains
                                <strong>
                                    ${persons.length}
                                </strong>
                                detected person(s).
                            </p>

                            <div
                                class="person-list"
                            >
                    `;


                    persons.forEach(
                        function(person, index) {

                            const personNumber =
                                person.person_id ||
                                (index + 1);


                            const hardHat =
                                person.hard_hat ||
                                "Not Detected";


                            const mask =
                                person.mask ||
                                "Not Detected";


                            const safetyVest =
                                person.safety_vest ||
                                "Not Detected";


                            const noHardHat =
                                person.no_hard_hat ||
                                "Not Detected";


                            const noMask =
                                person.no_mask ||
                                "Not Detected";


                            const noSafetyVest =
                                person.no_safety_vest ||
                                "Not Detected";


                            personSummaryHTML += `

                                <div
                                    class="person-card"
                                >

                                    <h4>
                                        👷 Person
                                        ${personNumber}
                                    </h4>

                                    <p>
                                        🪖
                                        <strong>
                                            Hard Hat:
                                        </strong>
                                        ${hardHat}
                                    </p>

                                    <p>
                                        😷
                                        <strong>
                                            Mask:
                                        </strong>
                                        ${mask}
                                    </p>

                                    <p>
                                        🦺
                                        <strong>
                                            Safety Vest:
                                        </strong>
                                        ${safetyVest}
                                    </p>

                                    <p>
                                        ⚠️
                                        <strong>
                                            No Hard Hat:
                                        </strong>
                                        ${noHardHat}
                                    </p>

                                    <p>
                                        ⚠️
                                        <strong>
                                            No Mask:
                                        </strong>
                                        ${noMask}
                                    </p>

                                    <p>
                                        ⚠️
                                        <strong>
                                            No Safety Vest:
                                        </strong>
                                        ${noSafetyVest}
                                    </p>

                                </div>
                            `;
                        }
                    );


                    personSummaryHTML += `

                            </div>

                        </div>
                    `;

                } else {

                    personSummaryHTML = `

                        <div
                            class="person-detection-summary"
                        >

                            <h3>
                                👷 Person-wise PPE Detection
                            </h3>

                            <p>
                                No person-specific
                                PPE information was
                                returned for this video.
                            </p>

                        </div>
                    `;
                }


                // ==================================
                // VIDEO RESULT
                // ==================================

                resultContent.innerHTML = `

                    <div class="result-media">

                        <video
                            class="result-video"
                            controls
                            preload="metadata"
                        >

                            <source
                                src="${data.result_url}"
                                type="video/mp4"
                            >

                            Your browser does not
                            support video playback.

                        </video>

                    </div>


                    <div
                        class="detection-summary"
                    >

                        <h3>
                            Video Detection Summary
                        </h3>

                        <p
                            class="detection-status"
                        >
                            ✓ PPE detection completed
                            successfully.
                        </p>

                        <p>
                            The video was analyzed
                            using the YOLO PPE
                            detection model.
                        </p>

                    </div>


                    ${personSummaryHTML}

                `;

            } catch (error) {

                resultContent.innerHTML = `

                    <div
                        class="empty-result"
                    >

                        <div
                            class="result-icon"
                        >
                            ❌
                        </div>

                        <h3>
                            Video Detection Failed
                        </h3>

                        <p>
                            ${error.message}
                        </p>

                    </div>
                `;
            }

        }
    );
}


// ==========================================
// PAGE LOAD
// ==========================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        showSection("home");

        setupImageDetection();

        setupVideoDetection();

    }
);