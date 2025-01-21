export interface Database {
  public: {
    Tables: {
      recipes: {
        Row: {
          id: string;
          title: string;
          instructions: string;
          prep_time: number | null;
          cook_time: number | null;
          servings: number | null;
          source_url: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          title: string;
          instructions: string;
          prep_time?: number | null;
          cook_time?: number | null;
          servings?: number | null;
          source_url?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          title?: string;
          instructions?: string;
          prep_time?: number | null;
          cook_time?: number | null;
          servings?: number | null;
          source_url?: string | null;
          created_at?: string;
        };
      };
      recipe_ingredients: {
        Row: {
          recipe_id: string;
          ingredient_id: string;
          quantity: number;
          unit: string;
        };
        Insert: {
          recipe_id: string;
          ingredient_id: string;
          quantity: number;
          unit: string;
        };
        Update: {
          recipe_id?: string;
          ingredient_id?: string;
          quantity?: number;
          unit?: string;
        };
      };
      users: {
        Row: {
          id: string;
          email: string;
          created_at: string;
          is_active: boolean;
          raw_user_meta_data: Record<string, unknown> | null;
        };
        Insert: {
          id?: string;
          email: string;
          created_at?: string;
          is_active?: boolean;
          raw_user_meta_data?: Record<string, unknown> | null;
        };
        Update: {
          id?: string;
          email?: string;
          created_at?: string;
          is_active?: boolean;
          raw_user_meta_data?: Record<string, unknown> | null;
        };
      };
      user_preferences: {
        Row: {
          id: string;
          user_id: string;
          spice_level: number;
        };
        Insert: {
          id?: string;
          user_id: string;
          spice_level: number;
        };
        Update: {
          id?: string;
          user_id?: string;
          spice_level?: number;
        };
      };
      pantry_items: {
        Row: {
          id: string;
          user_id: string;
          ingredient_id: string;
          quantity: number;
          unit: string;
          expiry_date: string | null;
          created_at: string;
        };
        Insert: {
          id?: string;
          user_id: string;
          ingredient_id: string;
          quantity: number;
          unit: string;
          expiry_date?: string | null;
          created_at?: string;
        };
        Update: {
          id?: string;
          user_id?: string;
          ingredient_id?: string;
          quantity?: number;
          unit?: string;
          expiry_date?: string | null;
          created_at?: string;
        };
      };
      categories: {
        Row: {
          id: string;
          name: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          created_at?: string;
        };
      };
      ingredients: {
        Row: {
          id: string;
          name: string;
          created_at: string;
        };
        Insert: {
          id?: string;
          name: string;
          created_at?: string;
        };
        Update: {
          id?: string;
          name?: string;
          created_at?: string;
        };
      };
    };
  };
}
