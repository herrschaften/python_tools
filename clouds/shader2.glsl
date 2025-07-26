// 3D Sphere Cloud with Raymarching + Pixelation
// Copy and paste this into Shadertoy

// === PARAMETERS ===
#define PIXEL_SIZE 32.0
#define CLOUD_CENTER vec3(0.0, 0.0, -3.0)
#define NUM_SPHERES 20
#define ANIMATION_SPEED 0.03
#define SKY_COLOR vec3(0.4, 0.7, 1.0)
// ==================

float noise3D(vec3 p) {
    // Simple 3D noise for organic movement
    return fract(sin(dot(p, vec3(127.3, 311.7, 521.1))) * 43758.5453123);
}

float smoothNoise3D(vec3 p) {
    vec3 i = floor(p);
    vec3 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    
    float a = noise3D(i);
    float b = noise3D(i + vec3(1.0, 0.0, 0.0));
    float c = noise3D(i + vec3(0.0, 1.0, 0.0));
    float d = noise3D(i + vec3(1.0, 1.0, 0.0));
    float e = noise3D(i + vec3(0.0, 0.0, 1.0));
    float g = noise3D(i + vec3(1.0, 0.0, 1.0));
    float h = noise3D(i + vec3(0.0, 1.0, 1.0));
    float k = noise3D(i + vec3(1.0, 1.0, 1.0));
    
    float x1 = mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
    float x2 = mix(mix(e, g, f.x), mix(h, k, f.x), f.y);
    
    return mix(x1, x2, f.z);
}

float hash(float n) {
    return fract(sin(n) * 43758.5453123);
}

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.3, 311.7))) * 43758.5453123);
}

// Distance to sphere
float sphereSDF(vec3 p, vec3 center, float radius) {
    return length(p - center) - radius;
}

// Generate cloud using multiple 3D spheres with organic movement
float cloudSDF(vec3 p) {
    float time = iTime * ANIMATION_SPEED;
    vec3 center = CLOUD_CENTER;
    
    float cloud = 999.0; // Start with large distance
    
    // Generate sphere positions procedurally with organic movement
    for(int i = 0; i < NUM_SPHERES; i++) {
        float fi = float(i);
        
        // Base position - more clustered around center
        float angle1 = fi * 2.4 + hash(fi * 0.1) * 6.28;
        float angle2 = hash(fi * 0.2) * 3.14;
        float radiusBase = 0.3 + hash(fi * 0.3) * 1.2;
        
        // Base sphere position
        vec3 basePos = center + vec3(
            cos(angle1) * sin(angle2) * radiusBase,
            cos(angle2) * radiusBase * 0.8,
            sin(angle1) * sin(angle2) * radiusBase
        );
        
        // Add organic 3D noise movement
        vec3 noiseOffset = vec3(
            smoothNoise3D(basePos * 2.0 + vec3(time * 0.5, 0.0, 0.0)) - 0.5,
            smoothNoise3D(basePos * 2.0 + vec3(0.0, time * 0.3, 0.0)) - 0.5,
            smoothNoise3D(basePos * 2.0 + vec3(0.0, 0.0, time * 0.4)) - 0.5
        ) * 0.4;
        
        // Add secondary movement layer for more complexity
        vec3 secondaryOffset = vec3(
            smoothNoise3D(basePos * 4.0 + vec3(time * 0.8, fi, 0.0)) - 0.5,
            smoothNoise3D(basePos * 4.0 + vec3(0.0, time * 0.6, fi)) - 0.5,
            smoothNoise3D(basePos * 4.0 + vec3(fi, 0.0, time * 0.7)) - 0.5
        ) * 0.2;
        
        // Final sphere position
        vec3 spherePos = basePos + noiseOffset + secondaryOffset;
        
        // Sphere size with some variation
        float sphereSize = 0.25 + hash(fi * 0.4) * 0.35;
        
        // Add sphere to cloud (union operation)
        float sphere = sphereSDF(p, spherePos, sphereSize);
        cloud = min(cloud, sphere);
    }
    
    return cloud;
}

// Raymarching function
float raymarch(vec3 ro, vec3 rd) {
    float t = 0.0;
    float maxDist = 20.0;
    
    for(int i = 0; i < 64; i++) {
        vec3 p = ro + rd * t;
        float d = cloudSDF(p);
        
        if(d < 0.01) {
            return t; // Hit cloud
        }
        
        if(t > maxDist) {
            return -1.0; // Missed
        }
        
        t += d * 0.5; // Step along ray
    }
    
    return -1.0;
}

// Calculate normal at surface point
vec3 getNormal(vec3 p) {
    float eps = 0.01;
    return normalize(vec3(
        cloudSDF(p + vec3(eps, 0, 0)) - cloudSDF(p - vec3(eps, 0, 0)),
        cloudSDF(p + vec3(0, eps, 0)) - cloudSDF(p - vec3(0, eps, 0)),
        cloudSDF(p + vec3(0, 0, eps)) - cloudSDF(p - vec3(0, 0, eps))
    ));
}

// 3D lighting calculation
float calculateLighting(vec3 p, vec3 normal) {
    vec3 lightDir = normalize(vec3(-0.5, 1.0, 0.3)); // Sun direction
    vec3 viewDir = normalize(-p); // Camera at origin
    
    // Diffuse lighting
    float diffuse = max(0.0, dot(normal, lightDir));
    
    // Ambient lighting
    float ambient = 0.3;
    
    // Simple specular
    vec3 reflectDir = reflect(-lightDir, normal);
    float specular = pow(max(0.0, dot(viewDir, reflectDir)), 16.0) * 0.5;
    
    return ambient + diffuse * 0.7 + specular;
}

// Convert lighting to 8-bit color palette
vec3 lightingToColor(float lighting) {
    // Quantize lighting
    lighting = floor(lighting * 6.0) / 6.0;
    
    if(lighting > 0.9) return vec3(1.0, 1.0, 1.0);        // Bright highlight
    if(lighting > 0.75) return vec3(0.95, 0.97, 1.0);     // Light highlight
    if(lighting > 0.6) return vec3(0.85, 0.9, 0.95);      // Medium light
    if(lighting > 0.45) return vec3(0.7, 0.75, 0.85);     // Light shadow
    if(lighting > 0.3) return vec3(0.55, 0.6, 0.75);      // Medium shadow
    return vec3(0.4, 0.45, 0.65);                         // Deep shadow
}

void mainImage(out vec4 fragColor, in vec2 fragCoord) {
    vec2 uv = fragCoord / iResolution.xy;
    
    // Pixelate the UV coordinates
    vec2 pixelUV = floor(uv * PIXEL_SIZE) / PIXEL_SIZE;
    
    // Convert to NDC coordinates
    vec2 ndc = pixelUV * 2.0 - 1.0;
    ndc.x *= iResolution.x / iResolution.y; // Aspect ratio correction
    
    // Set up camera
    vec3 rayOrigin = vec3(0.0, 0.0, 0.0);
    vec3 rayDirection = normalize(vec3(ndc, -1.0));
    
    // Raymarch the scene
    float t = raymarch(rayOrigin, rayDirection);
    
    vec3 finalColor = SKY_COLOR;
    
    if(t > 0.0) {
        // Hit the cloud - calculate lighting
        vec3 hitPoint = rayOrigin + rayDirection * t;
        vec3 normal = getNormal(hitPoint);
        float lighting = calculateLighting(hitPoint, normal);
        
        finalColor = lightingToColor(lighting);
    }
    
    fragColor = vec4(finalColor, 1.0);
}