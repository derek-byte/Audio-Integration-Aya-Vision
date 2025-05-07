import { CohereClientV2 } from "cohere-ai";

const client = new CohereClientV2({
  token: process.env.COHERE_API_KEY, // replace with actual key
});

export async function POST(req) {
  try {
    const { base64Image, message } = await req.json();
    console.log("📩 Server received:", { base64Image, message });

    const response = await client.chat({
      model: "c4ai-aya-vision-32b",
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: message },
            { type: "image_url", imageUrl: { url: base64Image } },
          ],
        },
      ],
      temperature: 0.3,
    });

    console.log("✅ Vision response:", response);

    return Response.json({ reply: response.message?.content?.[0]?.text || "No response" });
  } catch (err) {
    console.error("❌ API error:", err);
    return Response.json({ error: err.message }, { status: 500 });
  }
}
