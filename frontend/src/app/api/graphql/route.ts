export async function POST(request: Request) {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    
    if (!apiUrl) {
      return new Response(JSON.stringify({ error: 'API URL not configured' }), { status: 500 });
    }
  
    try {
      const cookies = request.headers.get('cookie') || '';
      const sessionToken = cookies.split('; ').find(c => c.startsWith('__session='))?.split('=')[1];
  
      if (!sessionToken) {
        return new Response(JSON.stringify({ error: 'Unauthorized' }), { status: 401 });
      }
  
      const body = await request.json();
  
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${sessionToken}`,
          'x-api-key': process.env.NEXT_PUBLIC_APPSYNC_API_KEY || ''
        },
        body: JSON.stringify(body)
      });
  
      const data = await response.json();
      return new Response(JSON.stringify(data), { status: response.status });
    } catch (error) {
      return new Response(JSON.stringify({ error: 'Internal error' }), { status: 500 });
    }
  }