import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const buffer = await request.arrayBuffer();
    const pdfBuffer = Buffer.from(buffer);

    // Create FormData and append the PDF file
    const formData = new FormData();
    const blob = new Blob([pdfBuffer], { type: 'application/pdf' });
    formData.append("file", blob, "document.pdf");

    // Forward to Python API using Docker network alias
    const response = await fetch("http://pdf-python:5001/api/verify-pdf", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Python API error: ${response.status}`);
    }

    const result = await response.json();
    return NextResponse.json(result);
  } catch (error) {
    console.error('Error checking PDF signature:', error);
    return NextResponse.json(
      { error: 'Failed to verify PDF signature' },
      { status: 500 }
    );
  }
}  