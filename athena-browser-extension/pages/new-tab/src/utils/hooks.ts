import { useMemo } from "react";
import { useAppConfig } from "../store";
import { collectModelsWithDefaultModel } from "./model";
import { DEFAULT_MODELS } from "../constant";

export function useAllModels() {
  const configStore = useAppConfig();
  const models = useMemo(() => {
    const customModels = "";
    const defaultModel = configStore.modelConfig.model;
    return collectModelsWithDefaultModel(
      DEFAULT_MODELS,
      customModels,
      defaultModel,
    );
  }, [configStore.modelConfig.model]);

  return models;
}
