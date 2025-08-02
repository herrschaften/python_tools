// 3D Sphere Cloud with Raymarching + Pixelation
// Copy and paste this into Shadertoy

// === PARAMETERS ===
#define PIXEL_SIZE 124.0
#define CLOUD_CENTER vec3(0.0, 0.0, -3.0)
#define NUM_SPHERES 20
#define ANIMATION_SPEED 0.03
#define SKY_COLOR vec3(0.4, 0.7, 1.0)
// ==================

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

// Generate cloud using multiple 3D spheres
float cloudSDF(vec3 p) {
    float time = iTime * ANIMATION_SPEED;
    vec3 center = CLOUD_CENTER;
    
    float cloud = 999.0; // Start with large distance
    
    // Generate sphere positions procedurally
    for(int i = 0; i < NUM_SPHERES; i++) {
        float fi = float(i);
        
        // Create unique position for each sphere
        float angle = fi * 2.4 + time;
        float height = hash(fi * 0.1) * 2.0 - 1.0; // Random height
        float radius_offset = hash(fi * 0.2) * 1.5 + 0.5;
        
        // Sphere position
        vec3 spherePos = center + vec3(
            cos(angle) * radius_offset * 0.8,
            height * 0.6 + sin(time + fi) * 0.1, // Slight animation
            sin(angle) * radius_offset * 0.8
        );
        
        // Sphere size
        float sphereSize = 0.3 + hash(fi * 0.3) * 0.4;
        
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