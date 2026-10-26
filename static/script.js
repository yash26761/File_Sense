document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const folderInput = document.getElementById("folderPathInput");
    const browseBtn = document.getElementById("browseBtn");
    const scanBtn = document.getElementById("scanBtn");
    const errorBox = document.getElementById("errorBox");
    const warningsBox = document.getElementById("warningsBox");
    const warningsList = document.getElementById("warningsList");
    const loadingIndicator = document.getElementById("loadingIndicator");
    const resultsContainer = document.getElementById("resultsContainer");

    // Summary Metric Elements
    const fileCountElem = document.getElementById("fileCount");
    const totalSizeElem = document.getElementById("totalSize");
    const duplicateGroupCountElem = document.getElementById("duplicateGroupCount");
    const recoverableSizeElem = document.getElementById("recoverableSize");
    const scannedPathElem = document.getElementById("scannedPath");

    // Section Counters & Containers
    const extTypeCounter = document.getElementById("extTypeCounter");
    const extensionTableBody = document.getElementById("extensionTableBody");
    const topFilesTableBody = document.getElementById("topFilesTableBody");
    const dupGroupBadge = document.getElementById("dupGroupBadge");
    const duplicateGroupsContainer = document.getElementById("duplicateGroupsContainer");
    const tableFileCounter = document.getElementById("tableFileCounter");
    const filesTableBody = document.getElementById("filesTableBody");

    function formatBytes(bytes) {
        if (typeof bytes !== "number" || isNaN(bytes) || bytes < 0) {
            return "0 B";
        }
        if (bytes === 0) return "0 B";
        const k = 1024;
        const sizes = ["B", "KB", "MB", "GB", "TB"];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        const index = Math.min(i, sizes.length - 1);
        const value = (bytes / Math.pow(k, index)).toFixed(index === 0 ? 0 : 2);
        return `${value} ${sizes[index]} (${bytes.toLocaleString()} B)`;
    }

    function clearMessages() {
        errorBox.hidden = true;
        errorBox.textContent = "";
        warningsBox.hidden = true;
        while (warningsList.firstChild) {
            warningsList.removeChild(warningsList.firstChild);
        }
    }

    function showError(message) {
        clearMessages();
        errorBox.textContent = message;
        errorBox.hidden = false;
    }

    function showWarnings(warnings) {
        while (warningsList.firstChild) {
            warningsList.removeChild(warningsList.firstChild);
        }

        if (Array.isArray(warnings) && warnings.length > 0) {
            warnings.forEach((warningText) => {
                const item = document.createElement("div");
                item.className = "warning-item";
                item.textContent = `• ${warningText}`;
                warningsList.appendChild(item);
            });
            warningsBox.hidden = false;
        } else {
            warningsBox.hidden = true;
        }
    }

    let isScanning = false;
    let isBrowsing = false;

    function setLoading(isLoading) {
        if (isLoading) {
            scanBtn.disabled = true;
            if (browseBtn) browseBtn.disabled = true;
            folderInput.disabled = true;
            loadingIndicator.hidden = false;
            loadingIndicator.style.display = "flex";
            resultsContainer.hidden = true;
            resultsContainer.style.display = "none";
            clearMessages();
        } else {
            scanBtn.disabled = false;
            if (browseBtn) browseBtn.disabled = false;
            folderInput.disabled = false;
            loadingIndicator.hidden = true;
            loadingIndicator.style.display = "none";
        }
    }

    async function handleBrowse() {
        if (isBrowsing || isScanning) {
            return;
        }

        isBrowsing = true;
        if (browseBtn) browseBtn.disabled = true;
        scanBtn.disabled = true;
        folderInput.disabled = true;
        const originalText = browseBtn ? browseBtn.textContent : "Browse Folder";
        if (browseBtn) browseBtn.textContent = "Selecting...";

        try {
            const response = await fetch("/api/browse", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                }
            });

            const data = await response.json().catch(() => null);

            if (!response.ok || !data || data.success === false) {
                const errMsg = (data && data.error) ? data.error : `Folder selection failed with status ${response.status}.`;
                showError(errMsg);
                return;
            }

            if (!data.cancelled && data.folder_path) {
                folderInput.value = data.folder_path;
                clearMessages();
            }
        } catch (err) {
            showError(`Network or request error: ${err.message || "Failed to communicate with local server."}`);
        } finally {
            isBrowsing = false;
            if (browseBtn) {
                browseBtn.textContent = originalText;
                browseBtn.disabled = false;
            }
            scanBtn.disabled = false;
            folderInput.disabled = false;
        }
    }

    async function handleScan() {
        if (isScanning || isBrowsing) {
            return;
        }

        const rawPath = folderInput.value ? folderInput.value.trim() : "";
        if (!rawPath) {
            showError("Please enter a valid directory path to scan.");
            folderInput.focus();
            return;
        }

        isScanning = true;
        setLoading(true);

        try {
            const response = await fetch("/api/scan", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ folder_path: rawPath })
            });

            const data = await response.json().catch(() => null);

            if (!response.ok || !data || data.success === false) {
                const errMsg = (data && data.error) ? data.error : `Scan failed with status ${response.status}.`;
                showError(errMsg);
                return;
            }

            renderDashboard(data);
        } catch (err) {
            showError(`Network or request error: ${err.message || "Failed to communicate with local server."}`);
        } finally {
            isScanning = false;
            setLoading(false);
        }
    }

    function renderDashboard(data) {
        // 1. Summary Metrics
        const totalFiles = Number(data.total_files || 0);
        const totalBytes = Number(data.total_size || 0);
        const dupGroups = Number(data.duplicate_group_count || 0);
        const recoverable = Number(data.recoverable_bytes || 0);

        fileCountElem.textContent = totalFiles.toLocaleString();
        totalSizeElem.textContent = formatBytes(totalBytes);
        duplicateGroupCountElem.textContent = dupGroups.toLocaleString();
        recoverableSizeElem.textContent = formatBytes(recoverable);
        scannedPathElem.textContent = data.folder_path || "";

        // 2. Warnings
        showWarnings(data.warnings);

        // 3. Storage by File Extension
        renderExtensionSummary(data.extension_summary);

        // 4. Top 10 Largest Files
        renderTopFiles(data.top_10_largest);

        // 5. Duplicate Groups
        renderDuplicateGroups(data.duplicate_groups);

        // 6. All Discovered Files
        renderAllFiles(data.files);

        resultsContainer.hidden = false;
        resultsContainer.style.display = "flex";
    }

    function renderExtensionSummary(extensions) {
        while (extensionTableBody.firstChild) {
            extensionTableBody.removeChild(extensionTableBody.firstChild);
        }

        const extList = Array.isArray(extensions) ? extensions : [];
        extTypeCounter.textContent = `${extList.length} types`;

        if (extList.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 3;
            cell.className = "empty-cell";
            cell.textContent = "No file extensions to summarize.";
            row.appendChild(cell);
            extensionTableBody.appendChild(row);
            return;
        }

        extList.forEach((item) => {
            const row = document.createElement("tr");

            const extCell = document.createElement("td");
            extCell.textContent = item.extension || "(no extension)";

            const countCell = document.createElement("td");
            countCell.textContent = Number(item.count || 0).toLocaleString();

            const sizeCell = document.createElement("td");
            sizeCell.textContent = formatBytes(item.total_size || 0);

            row.appendChild(extCell);
            row.appendChild(countCell);
            row.appendChild(sizeCell);

            extensionTableBody.appendChild(row);
        });
    }

    function renderTopFiles(topFiles) {
        while (topFilesTableBody.firstChild) {
            topFilesTableBody.removeChild(topFilesTableBody.firstChild);
        }

        const list = Array.isArray(topFiles) ? topFiles : [];

        if (list.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 3;
            cell.className = "empty-cell";
            cell.textContent = "No files found.";
            row.appendChild(cell);
            topFilesTableBody.appendChild(row);
            return;
        }

        list.forEach((item, index) => {
            const row = document.createElement("tr");

            const rankCell = document.createElement("td");
            rankCell.textContent = (index + 1).toString();

            const nameCell = document.createElement("td");
            nameCell.textContent = item.name || "";
            nameCell.title = item.path || "";

            const sizeCell = document.createElement("td");
            sizeCell.textContent = formatBytes(item.size || 0);

            row.appendChild(rankCell);
            row.appendChild(nameCell);
            row.appendChild(sizeCell);

            topFilesTableBody.appendChild(row);
        });
    }

    function renderDuplicateGroups(duplicateGroups) {
        while (duplicateGroupsContainer.firstChild) {
            duplicateGroupsContainer.removeChild(duplicateGroupsContainer.firstChild);
        }

        const groups = Array.isArray(duplicateGroups) ? duplicateGroups : [];
        dupGroupBadge.textContent = `${groups.length} groups`;

        if (groups.length === 0) {
            const emptyMsg = document.createElement("div");
            emptyMsg.className = "empty-cell";
            emptyMsg.textContent = "No duplicate files detected in this folder.";
            duplicateGroupsContainer.appendChild(emptyMsg);
            return;
        }

        groups.forEach((group, index) => {
            const groupCard = document.createElement("div");
            groupCard.className = "dup-group-card";

            // Header
            const header = document.createElement("div");
            header.className = "dup-group-header";

            const meta = document.createElement("div");
            meta.className = "dup-group-meta";

            const title = document.createElement("div");
            title.className = "dup-group-title";
            title.textContent = `Group #${index + 1} (${group.count} identical copies)`;

            const hashLabel = document.createElement("span");
            hashLabel.className = "dup-hash-label";
            const shortHash = group.hash ? group.hash.substring(0, 16) : "";
            hashLabel.textContent = `SHA-256: ${shortHash}... | Each: ${formatBytes(group.size || 0)}`;

            meta.appendChild(title);
            meta.appendChild(hashLabel);

            const stats = document.createElement("div");
            stats.className = "dup-group-stats";

            const recBadge = document.createElement("span");
            recBadge.className = "badge badge-success";
            recBadge.textContent = `Recoverable: ${formatBytes(group.recoverable_bytes || 0)}`;

            stats.appendChild(recBadge);
            header.appendChild(meta);
            header.appendChild(stats);

            // Paths List
            const pathsList = document.createElement("ul");
            pathsList.className = "dup-paths-list";

            const groupFiles = Array.isArray(group.files) ? group.files : [];
            groupFiles.forEach((file) => {
                const li = document.createElement("li");
                li.className = "dup-path-item";

                const bullet = document.createElement("span");
                bullet.className = "dup-path-bullet";
                bullet.textContent = "↳";

                const textSpan = document.createElement("span");
                textSpan.textContent = file.path || file.name || "";

                li.appendChild(bullet);
                li.appendChild(textSpan);
                pathsList.appendChild(li);
            });

            groupCard.appendChild(header);
            groupCard.appendChild(pathsList);
            duplicateGroupsContainer.appendChild(groupCard);
        });
    }

    function renderAllFiles(files) {
        while (filesTableBody.firstChild) {
            filesTableBody.removeChild(filesTableBody.firstChild);
        }

        const fileList = Array.isArray(files) ? files : [];
        tableFileCounter.textContent = `${fileList.length.toLocaleString()} items`;

        if (fileList.length === 0) {
            const row = document.createElement("tr");
            const cell = document.createElement("td");
            cell.colSpan = 4;
            cell.className = "empty-cell";
            cell.textContent = "No files found in directory.";
            row.appendChild(cell);
            filesTableBody.appendChild(row);
            return;
        }

        fileList.forEach((file) => {
            const row = document.createElement("tr");

            const nameCell = document.createElement("td");
            nameCell.textContent = file.name || "";

            const extCell = document.createElement("td");
            extCell.textContent = file.extension || "";

            const sizeCell = document.createElement("td");
            sizeCell.textContent = formatBytes(file.size || 0);

            const pathCell = document.createElement("td");
            pathCell.className = "file-path-cell";
            pathCell.textContent = file.path || "";

            row.appendChild(nameCell);
            row.appendChild(extCell);
            row.appendChild(sizeCell);
            row.appendChild(pathCell);

            filesTableBody.appendChild(row);
        });
    }

    // Event Listeners
    if (browseBtn) {
        browseBtn.addEventListener("click", handleBrowse);
    }
    scanBtn.addEventListener("click", handleScan);

    folderInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            handleScan();
        }
    });
});
