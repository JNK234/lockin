function scrapePageContext() {
    // Grab the main text, stripping out excessive whitespace
    let pageText = document.body.innerText.replace(/\s+/g, ' ').trim();

    // Truncate to the first 2000 characters to save LLM tokens and latency
    let truncatedText = pageText.substring(0, 2000);

    return {
        title: document.title,
        url: window.location.href,
        content: truncatedText,
        timestamp: new Date().toISOString()
    };
}

// Execute and return the data to the background worker
scrapePageContext();