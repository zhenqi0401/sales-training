const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Try to read the docx using the zip approach with Node
// First, let's check if we can find a docx parsing library or use adm-zip
try {
    // Try installing and using a simple approach
    const AdmZip = require('adm-zip');
    const xml2js = require('xml2js');
    
    const filePath = 'E:\\Sales Training System\\.reasonix\\attachments\\clipboard-20260611-175046.279109-000002.docx';
    const zip = new AdmZip(filePath);
    const xml = zip.readAsText('word/document.xml');
    
    // Simple regex to extract text between <w:t> tags
    const textMatches = xml.match(/<w:t[^>]*>([^<]*)<\/w:t>/g);
    if (textMatches) {
        const texts = textMatches.map(m => m.replace(/<[^>]+>/g, ''));
        // Group by paragraph (simplistic)
        let currentPara = [];
        // Better: use a proper parser
        // Just output all text for now
        console.log(texts.join(''));
    }
} catch (e) {
    console.log('Error:', e.message);
    // Fallback: use zip and manual parsing
}
