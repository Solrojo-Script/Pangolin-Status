// Pangolin CLI may print an update notice before its JSON response.
export function isClientConnected(output) {
    const start = output.indexOf('{');
    const end = output.lastIndexOf('}');
    if (start < 0 || end < start)
        return false;

    try {
        const status = JSON.parse(output.slice(start, end + 1));
        return status.connected === true &&
            status.registered === true &&
            status.terminated === false;
    } catch (_) {
        return false;
    }
}
