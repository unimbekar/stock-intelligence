import fs from "node:fs";
import path from "node:path";

export type Product = {
  name: string;
  tagline: string;
  dataModeLabel: string;
  disclaimer: string;
  targetScenario: {
    capital: number;
    dailyProfitTarget: number;
    note: string;
  };
  scoringWeights: Record<string, number>;
};

export function readProduct(): Product {
  const candidates = [
    process.env.PRODUCT_CONFIG_PATH,
    path.join(process.cwd(), "../../packages/config/product.json"),
    path.join(process.cwd(), "packages/config/product.json"),
    path.join(process.cwd(), "product.json"),
  ].filter((value): value is string => Boolean(value));

  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return JSON.parse(fs.readFileSync(candidate, "utf8")) as Product;
    }
  }
  throw new Error("product.json was not found");
}

export function requiredReturn(capital: number, target: number): number {
  return (target / capital) * 100;
}
